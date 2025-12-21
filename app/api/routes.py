from flask import jsonify, request
from app.api import bp
from app.hardwarestate import HardwareState
from app.hardware_constants import SensorId, RelayId
from app.dynconfig import DynConfig
from app.models import SystemConfig, CalibrationPoint
from app import db
from app.regulation import Regulator
from app.calibration import CalibrationRegistry
from flask_login import login_required
import os

@bp.route('/status', methods=['GET'])
def get_status():
    """ Returns current system status including sensor readings and relay states """
    
    # Get sensor readings
    readings = {}
    for sensor_id, reading in HardwareState.cur_sensor_values.items():
        if reading:
            readings[sensor_id.name] = {
                'raw': reading.raw,
                'calibrated': reading.cald
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
        'is_day': not Regulator()._is_light_out(), # _is_light_out returns True if it is night
        'manual_mode': DynConfig.manual_mode,
        'circuit_enables': DynConfig.circuit_states
    })

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
        # We need to update the SystemConfig entry for 'circuit_states'
        # DynConfig.circuit_states is a property, setting it might not update DB automatically unless we implemented a setter.
        # The current implementation of DynConfig uses classproperty which is usually read-only or needs a setter.
        # Let's check DynConfig implementation. It seems it just reads from _confDict.
        # So we need to update SystemConfig model and then reload DynConfig.
        
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

@bp.route('/config', methods=['GET'])
@login_required
def get_config():
    """ Get all dynamic config values and their definitions """
    definitions = DynConfig.get_definitions()
    config_values = {}
    
    # We can iterate over definitions to get keys
    for key, meta in definitions.items():
        # Get current value
        # We can access it via getattr(DynConfig, key)
        val = getattr(DynConfig, key)
        config_values[key] = {
            'value': val,
            'default': meta['default'],
            'description': meta['description'],
            'is_eval': meta['is_eval']
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
        data[sensor.name] = [{'id': p.id, 'measured': p.measured_val, 'actual': p.actual_val} for p in points]
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

