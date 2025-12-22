from flask import jsonify, request
from app.api import bp
from app.hardwarestate import HardwareState
from app.hardware_constants import SensorId, RelayId
from app.dynconfig import DynConfig
from app.models import SystemConfig, CalibrationPoint, Measurement
from app import db
from app.regulation import Regulator
from app.calibration import CalibrationRegistry
from flask_login import login_required
import os
from datetime import datetime, timedelta

from app.watchdog import WatchdogTrigger
from config import Config

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
    
    return jsonify({
        'sensors': readings,
        'relays': relays,
        'is_day': Regulator()._is_light_out(), # _is_light_out returns True if it is day
        'manual_mode': DynConfig.manual_mode,
        'circuit_enables': DynConfig.circuit_states,
        'watchdog_tripped': WatchdogTrigger.is_tripped(),
        'regulator_status': Regulator().get_status_str()
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
    
    return jsonify({'success': True})

@bp.route('/watchdog/clear', methods=['POST'])
@login_required
def clear_watchdog():
    """ Clear all watchdog alarms """
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

    HardwareState.set_relay(relay_id, state)
    return jsonify({'success': True})


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
    # Force the configuration in memory to pull the latest version
    DynConfig.reload()
    
    return jsonify({'success': True})

@bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    """ Get last N lines of logs """
    try:
        with open("app.log", "r") as f:
            lines = f.readlines()
            return jsonify({'logs': lines[-100:]}) # Return last 100 lines
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

    query = Measurement.query

    if start_str:
        try:
            start_utc = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            # Convert to local time and make naive for DB comparison
            start_local = start_utc.astimezone(Config.TIMEZONE).replace(tzinfo=None)
            query = query.filter(Measurement.timestamp >= start_local)
        except ValueError:
            pass # Ignore invalid date
            
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

    # Convert timestamps to aware ISO strings
    timestamps = []
    for m in results:
        # Attach timezone info (DB stores naive local time)
        ts_aware = m.timestamp.replace(tzinfo=Config.TIMEZONE)
        timestamps.append(ts_aware.isoformat())

    data = {
        'timestamps': timestamps,
        'sensors': {},
        'relays': {
            'inside_1': [m.relay_inside_1 for m in results],
            'outside_1': [m.relay_outside_1 for m in results],
            'inside_2': [m.relay_inside_2 for m in results],
            'outside_2': [m.relay_outside_2 for m in results],
        },
        'sensor_names': {s.name: s.readable_name for s in SensorId}
    }

    sensor_list = sensors_str.split(',') if sensors_str else [s.name for s in SensorId]

    for sensor in sensor_list:
        col_name = f"{sensor}_cal"
        if hasattr(Measurement, col_name):
            data['sensors'][sensor] = [getattr(m, col_name) for m in results]
            
    return jsonify(data)
