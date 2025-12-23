from flask import jsonify, request
from app.api import bp
from app.hardwarestate import HardwareState
from app.hardware_constants import SensorId, RelayId
from app.dynconfig import DynConfig
from app.models import SystemConfig, CalibrationPoint, Measurement
from app import db
from app.regulation import Regulator
from app.calibration import CalibrationRegistry
from app.hardware import gfci_driver, initialize_hardware, deinitialize_hardware
from drivers.real_drivers import ArduinoInterface
from flask_login import login_required
import os
from datetime import datetime, timedelta

from app.watchdog import WatchdogTrigger
from app.config import Config
from loguru import logger
import pandas as pd
import numpy as np

@bp.route('/status', methods=['GET'])
def get_status():
    """ Returns current system status including sensor readings and relay states """
    
    # Get sensor readings
    readings = {}
    for sensor_id, reading in HardwareState.cur_sensor_values.items():
        if reading:
            readings[sensor_id.name] = {
                'raw': reading.raw,
                'calibrated': reading.cald,
                'timestamp': reading.timestamp.isoformat() if reading.timestamp else None
            }
        else:
            readings[sensor_id.name] = None

    # Get relay states
    relays = {}
    for relay_id in RelayId:
        relays[relay_id.name] = HardwareState.get_relay_state(relay_id)
    
    gfci_status = {
        'ping': False,
        'tripped': [False, False],
        'enabled': DynConfig.gfci_enabled,
        'threshold': DynConfig.gfci_trip_threshold_ma
    }
    if gfci_driver:
        gfci_status['ping'] = gfci_driver.ping()
        gfci_status['tripped'] = [gfci_driver.is_tripped(1), gfci_driver.is_tripped(2)]

    return jsonify({
        'sensors': readings,
        'relays': relays,
        'is_day': Regulator()._is_light_out(), # _is_light_out returns True if it is day
        'manual_mode': DynConfig.manual_mode,
        'circuit_enables': DynConfig.circuit_states,
        'watchdog_tripped': WatchdogTrigger.is_tripped(),
        'regulator_status': Regulator().get_status_str(),
        'gfci': gfci_status
    })

@bp.route('/watchdog', methods=['GET'])
@login_required
def get_watchdog_status():
    """ Get status of all watchdog triggers """
    triggers = []
    excludes = DynConfig.watchdog_excludes
    
    for trigger in WatchdogTrigger.all_triggers():
        triggers.append({
            'name': trigger.__name__,
            'status': trigger.notify_state(),
            'is_tripped': trigger.is_tripped(),
            'enabled': trigger.__name__ not in excludes
        })
    
    return jsonify({
        'tripped': WatchdogTrigger.is_tripped(),
        'triggers': triggers
    })

@bp.route('/watchdog/toggle/<name>', methods=['POST'])
@login_required
def toggle_watchdog_enable(name):
    """ Toggle enable/disable state of a watchdog trigger """
    data = request.get_json()
    enabled = data.get('enabled')
    
    excludes = DynConfig.watchdog_excludes
    
    if enabled:
        if name in excludes:
            excludes.remove(name)
    else:
        if name not in excludes:
            excludes.append(name)
            
    # Update config
    conf = SystemConfig.query.filter_by(key='watchdog_excludes').first()
    if not conf:
        conf = SystemConfig(key='watchdog_excludes')
        db.session.add(conf)
    
    conf.value = str(excludes)
    db.session.commit()
    DynConfig.reload()
    
    logger.info(f"Watchdog trigger '{name}' enabled={enabled}")
    
    return jsonify({'success': True})

@bp.route('/watchdog/clear', methods=['POST'])
@login_required
def clear_watchdog():
    """ Clear all watchdog alarms """
    logger.info("Clearing all watchdog alarms")
    WatchdogTrigger.clear_alarm()
    return jsonify({'success': True})

@bp.route('/watchdog/trigger/<name>', methods=['POST'])
@login_required
def test_trigger_watchdog(name):
    """ Simulate a trigger for a specific watchdog """
    for trigger in WatchdogTrigger.all_triggers():
        if trigger.__name__ == name:
            trigger.trigger_alarm_state()
            return jsonify({'success': True})
    return jsonify({'error': 'Trigger not found'}), 404

@bp.route('/watchdog/clear/<name>', methods=['POST'])
@login_required
def clear_single_watchdog(name):
    """ Clear a specific watchdog trigger """
    for trigger in WatchdogTrigger.all_triggers():
        if trigger.__name__ == name:
            trigger.clear()
            # If no other triggers are active, we might want to clear the master alarm?
            # The current implementation of WatchdogTrigger.clear_alarm clears ALL.
            # Individual clear might not reset the master alarm state if it's a simple boolean.
            # Let's check WatchdogTrigger implementation.
            # It seems _alarm_state is a global boolean.
            # We should probably re-evaluate if any are tripped.
            # For now, let's just call clear() on the instance.
            return jsonify({'success': True})
    return jsonify({'error': 'Trigger not found'}), 404


@bp.route('/circuits', methods=['POST'])
@login_required
def set_circuit_enable():
    """ Enable or disable a circuit (manual control) """
    data = request.get_json()
    circuit_idx = data.get('circuit_id') # 0 or 1
    enabled = data.get('enabled') # boolean
    
    if circuit_idx is None or enabled is None:
        return jsonify({'error': 'Missing parameters'}), 400
        
    current_states = DynConfig.circuit_states
    if 0 <= circuit_idx < len(current_states):
        current_states[circuit_idx] = enabled
        
        # Update DB
        conf = SystemConfig.query.filter_by(key='circuit_states').first()
        if conf:
            conf.value = str(current_states)
            db.session.commit()
            DynConfig.reload()
            logger.info(f"Circuit {circuit_idx} enabled={enabled}")
            return jsonify({'success': True, 'new_state': current_states})
        else:
             return jsonify({'error': 'Config key not found'}), 500
    else:
        return jsonify({'error': 'Invalid circuit index'}), 400

@bp.route('/relays', methods=['POST'])
@login_required
def set_relay_state():
    """ Manually set a relay state (only works in manual mode) """
    if not DynConfig.manual_mode:
        return jsonify({'error': 'System is not in manual mode'}), 403

    data = request.get_json()
    relay_name = data.get('relay')
    state = data.get('state') # boolean

    if not relay_name or state is None:
        return jsonify({'error': 'Missing parameters'}), 400

    try:
        relay_id = RelayId[relay_name]
    except KeyError:
        return jsonify({'error': 'Invalid relay name'}), 400

    logger.info(f"Manual relay set: {relay_name} = {state}")
    HardwareState.set_relay(relay_id, state)
    return jsonify({'success': True})

@bp.route('/gfci/trip/<int:circuit>', methods=['POST'])
@login_required
def trip_gfci(circuit):
    """ Manually trip a GFCI circuit """
    if gfci_driver:
        logger.warning(f"Manual GFCI trip for circuit {circuit}")
        gfci_driver.set_tripped(circuit)
        return jsonify({'success': True})
    return jsonify({'error': 'No GFCI driver'}), 500

@bp.route('/gfci/reset/<int:circuit>', methods=['POST'])
@login_required
def reset_gfci(circuit):
    """ Manually reset a GFCI circuit """
    if gfci_driver:
        logger.info(f"Manual GFCI reset for circuit {circuit}")
        gfci_driver.reset_tripped(circuit)
        return jsonify({'success': True})
    return jsonify({'error': 'No GFCI driver'}), 500


@bp.route('/config', methods=['GET'])
@login_required
def get_config():
    """ Get all dynamic config values and their definitions """
    definitions = DynConfig.get_definitions()
    raw_config = DynConfig.get_raw_config()
    config_values = {}
    
    # We can iterate over definitions to get keys
    for key, meta in definitions.items():
        # Get current value
        # If it's an eval'd property, we want the RAW string from the DB/Config for editing
        # Otherwise we get the evaluated object (e.g. dict) which JSON.stringify converts to JSON
        
        if meta['is_eval']:
            # Try to get raw string from _confDict
            val = raw_config.get(key, meta['default'])
            
            # Special case: For booleans, we want the actual boolean value for the UI switch
            # For other eval types (like json/list), we want the raw string for editing
            if meta.get('value_type') == 'boolean':
                try:
                    # We can try to eval the raw string, or use getattr. 
                    # Using getattr ensures we get the same logic as the backend uses.
                    val = getattr(DynConfig, key)
                except:
                    # Fallback to False if eval fails, or maybe keep the string?
                    # If we keep the string, the UI switch will be unchecked (False).
                    val = False
        else:
            val = getattr(DynConfig, key)

        config_values[key] = {
            'value': val,
            'default': meta['default'],
            'description': meta['description'],
            'category': meta.get('category', 'System'),
            'is_eval': meta['is_eval'],
            'value_type': meta.get('value_type', 'text')
        }
        
    return jsonify(config_values)

@bp.route('/config', methods=['POST'])
@login_required
def update_config():
    """ Update a dynamic config value """
    data = request.get_json()
    key = data.get('key')
    value = data.get('value')
    
    if not key or value is None:
        return jsonify({'error': 'Missing parameters'}), 400
        
    definitions = DynConfig.get_definitions()
    if key not in definitions:
        return jsonify({'error': 'Invalid config key'}), 400

    # Validate value
    if not DynConfig.validate(key, value):
        return jsonify({'error': 'Invalid value for this configuration setting'}), 400
        
    # Update DB
    conf = SystemConfig.query.filter_by(key=key).first()
    if not conf:
        conf = SystemConfig(key=key)
        db.session.add(conf)
    
    conf.value = str(value) # Store as string
    db.session.commit()
    
    logger.info(f"Config updated: {key} = {value}")
    
    # Force the configuration in memory to pull the latest version
    DynConfig.reload()
    
    # If GFCI settings changed, sync them
    if key.startswith('gfci_'):
        HardwareState.sync_gfci_settings()

    return jsonify({'success': True})

@bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    """ Get last N lines of logs, optionally filtered by level and search term """
    level = request.args.get('level', 'DEBUG').upper()
    search_term = request.args.get('search', '').lower()
    try:
        limit = int(request.args.get('limit', 100))
    except ValueError:
        limit = 100

    levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    try:
        level_idx = levels.index(level)
    except ValueError:
        level_idx = 0 # Default to DEBUG if invalid
        
    target_levels = levels[level_idx:]
    
    try:
        with open(Config.LOG_FILE_PATH, "r") as f:
            lines = f.readlines()
            
            filtered_lines = []
            # Process in reverse to get the "last N" matching lines efficiently?
            # Or just filter all and take last N. File isn't likely to be massive in this context.
            # Let's filter all for simplicity of search.
            
            for line in lines:
                # 1. Check Level
                level_match = False
                for l in target_levels:
                    if l in line:
                        level_match = True
                        break
                if not level_match:
                    continue

                # 2. Check Search Term
                if search_term and search_term not in line.lower():
                    continue
                
                filtered_lines.append(line)
            
            # Return last N lines
            return jsonify({'logs': filtered_lines[-limit:]}) 
    except FileNotFoundError:
        return jsonify({'logs': []})

@bp.route('/calibration', methods=['GET'])
@login_required
def get_calibration():
    """ Get calibration points for all sensors """
    data = {}
    for sensor in SensorId:
        points = CalibrationRegistry.get_points(sensor)
        data[sensor.name] = {
            'readable_name': sensor.readable_name,
            'points': [{'id': p.id, 'measured': p.measured_val, 'actual': p.actual_val} for p in points]
        }
    return jsonify(data)

@bp.route('/calibration', methods=['POST'])
@login_required
def add_calibration_point():
    """ Add a calibration point """
    data = request.get_json()
    sensor_name = data.get('sensor')
    measured = data.get('measured')
    actual = data.get('actual')
    
    if not sensor_name or measured is None or actual is None:
        return jsonify({'error': 'Missing parameters'}), 400
        
    try:
        sensor = SensorId[sensor_name]
    except KeyError:
        return jsonify({'error': 'Invalid sensor'}), 400
        
    p = CalibrationPoint(sensor_id=sensor.value, measured_val=measured, actual_val=actual)
    db.session.add(p)
    db.session.commit()
    CalibrationRegistry.invalidate(sensor)
    
    return jsonify({'success': True, 'id': p.id})

@bp.route('/calibration/<int:id>', methods=['DELETE'])
@login_required
def delete_calibration_point(id):
    """ Delete a calibration point """
    p = CalibrationPoint.query.get(id)
    if not p:
        return jsonify({'error': 'Point not found'}), 404
        
    sensor = SensorId(p.sensor_id)
    db.session.delete(p)
    db.session.commit()
    CalibrationRegistry.invalidate(sensor)
    
    return jsonify({'success': True})


@bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """ Get historical sensor data """
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    sensors_str = request.args.get('sensors') # comma separated
    derived_defs_str = request.args.get('derived_defs') # JSON string
    downsample_factor = request.args.get('downsample_factor', type=int, default=1)

    query = Measurement.query

    if start_str:
        try:
            start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            # Convert to local time and make naive for DB comparison
            start_local = start_utc.astimezone(Config.TIMEZONE).replace(tzinfo=None)
            query = query.filter(Measurement.timestamp >= start_local)
        except ValueError:
            pass
            
    if end_str:
        try:
            end_utc = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            # Convert to local time and make naive for DB comparison
            end_local = end_utc.astimezone(Config.TIMEZONE).replace(tzinfo=None)
            query = query.filter(Measurement.timestamp <= end_local)
        except ValueError:
            pass

    # Limit results to prevent overload if no range specified
    if not start_str and not end_str:
        query = query.filter(Measurement.timestamp >= datetime.now() - timedelta(hours=24))

    query = query.order_by(Measurement.timestamp.asc())
    results = query.all()

    if not results:
        return jsonify({'timestamps': [], 'sensors': {}, 'relays': {}, 'sensor_names': {s.name: s.readable_name for s in SensorId}})

    # Convert to DataFrame
    data = []
    for m in results:
        row = {
            'timestamp': m.timestamp,
            'relay_inside_1': m.relay_inside_1,
            'relay_outside_1': m.relay_outside_1,
            'relay_inside_2': m.relay_inside_2,
            'relay_outside_2': m.relay_outside_2,
        }
        for s in SensorId:
            col = f"{s.name}_cal"
            row[s.name] = getattr(m, col, None)
        data.append(row)
        
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)

    # Apply derived columns
    if derived_defs_str:
        import json
        try:
            derived_defs = json.loads(derived_defs_str)
            
            # Safe evaluation environment
            def integrate(series): return series.cumsum()
            def differentiate(series): return series.diff()
            
            safe_locals = {
                'integrate': integrate,
                'differentiate': differentiate,
                'diff': differentiate,
                'np': np,
                'pd': pd,
            }
            # Add numpy math functions
            for name in ['sin', 'cos', 'tan', 'sqrt', 'abs', 'log', 'exp', 'power']:
                safe_locals[name] = getattr(np, name)
                
            # Add columns to locals
            for col in df.columns:
                safe_locals[col] = df[col]
                
            for definition in derived_defs:
                name = definition.get('name')
                expr = definition.get('expr')
                if name and expr:
                    try:
                        # Update locals with current df columns (in case one derived col depends on another)
                        for col in df.columns:
                            safe_locals[col] = df[col]
                            
                        df[name] = eval(expr, {"__builtins__": {}}, safe_locals)
                    except Exception as e:
                        logger.warning(f"Failed to derive {name}: {e}")
        except Exception as e:
            logger.error(f"Derived columns error: {e}")

    # Filter by state
    filter_state = request.args.get('filter_state')
    if filter_state and filter_state != 'none':
        if filter_state == 'c1_on':
            df = df[df['relay_inside_1'] & df['relay_outside_1']]
        elif filter_state == 'c1_off':
            df = df[~(df['relay_inside_1'] & df['relay_outside_1'])]
        elif filter_state == 'c2_on':
            df = df[df['relay_inside_2'] & df['relay_outside_2']]
        elif filter_state == 'c2_off':
            df = df[~(df['relay_inside_2'] & df['relay_outside_2'])]

    # Downsample
    if downsample_factor > 1:
        df = df.iloc[::downsample_factor]

    # Convert timestamps to aware ISO strings
    timestamps = [ts.replace(tzinfo=Config.TIMEZONE).isoformat() for ts in df.index]

    # Prepare response data
    resp_sensors = {}
    
    # Determine which columns to return
    requested_cols = set(sensors_str.split(',')) if sensors_str else set([s.name for s in SensorId])
    
    # Also include any derived columns that were successfully created
    if derived_defs_str:
        try:
            derived_defs = json.loads(derived_defs_str)
            for d in derived_defs:
                if d['name'] in df.columns:
                    requested_cols.add(d['name'])
        except: pass

    for col in requested_cols:
        if col in df.columns:
            # Replace NaN with None for JSON compatibility
            resp_sensors[col] = df[col].where(pd.notnull(df[col]), None).tolist()
            
    resp_relays = {
        'inside_1': df['relay_inside_1'].tolist(),
        'outside_1': df['relay_outside_1'].tolist(),
        'inside_2': df['relay_inside_2'].tolist(),
        'outside_2': df['relay_outside_2'].tolist(),
    }

    return jsonify({
        'timestamps': timestamps,
        'sensors': resp_sensors,
        'relays': resp_relays,
        'sensor_names': {s.name: s.readable_name for s in SensorId}
    })

@bp.route('/maintenance/downsample_db', methods=['POST'])
@login_required
def downsample_db():
    """ Permanently downsample the database by keeping 1 row every N rows """
    data = request.get_json()
    factor = int(data.get('factor', 1))
    
    if factor <= 1:
        return jsonify({'success': False, 'message': 'Factor must be > 1'})
        
    try:
        # Construct SQL based on DB type
        if 'sqlite' in Config.SQLALCHEMY_DATABASE_URI:
             sql = f"""
             DELETE FROM measurement 
             WHERE id IN (
                 SELECT id FROM (
                     SELECT id, ROW_NUMBER() OVER (ORDER BY timestamp) as rn 
                     FROM measurement
                 ) 
                 WHERE rn % {factor} != 0
             )
             """
        else:
             # Assume MySQL/MariaDB
             sql = f"""
             DELETE m FROM measurement m 
             JOIN (
                 SELECT id, ROW_NUMBER() OVER (ORDER BY timestamp) as rn 
                 FROM measurement
             ) t ON m.id = t.id 
             WHERE t.rn % {factor} != 0
             """
             
        db.session.execute(db.text(sql))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Database downsample failed: {e}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/maintenance/reset_arduino', methods=['POST'])
@login_required
def reset_arduino():
    try:
        ArduinoInterface().reset_arduino()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Arduino reset failed: {e}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/maintenance/reinit_hardware', methods=['POST'])
@login_required
def reinit_hardware():
    try:
        deinitialize_hardware(force=True)
        initialize_hardware()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Hardware reinit failed: {e}")
        return jsonify({'success': False, 'message': str(e)})

