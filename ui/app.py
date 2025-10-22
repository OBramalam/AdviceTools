from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
import sys
import json
from datetime import datetime
import traceback

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import ParserService, SimulationService
from services.risk_indicator_service import calculate_risk_indicator
from schemas.base_schemas import AdviserConfig, Profile, RecurringCashFlow
from simulation_engine.common.types import CashFlow, SimulationPortfolioWeights
from common.utils import to_annual
import datetime as dt
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Parse the conversation
            parser = ParserService(user_id=1, filepath=filepath)
            profile, cash_flows = parser.extract_data()
            
            
            adviser_config = AdviserConfig()

            session_data = {
                'profile': profile.model_dump(mode='json'),
                'cash_flows': [cf.model_dump(mode='json') for cf in cash_flows],
                'adviser_config': adviser_config.model_dump(mode='json'),
                'filepath': filepath
            }
            
            return render_template('simulation.html', 
                                profile=profile, 
                                cash_flows=cash_flows,
                                session_data=json.dumps(session_data))
            
        except Exception as e:
            flash(f'Error parsing conversation: {str(e)}')
            return redirect(url_for('index'))
    
    flash('Invalid file type. Please upload a .txt file.')
    return redirect(url_for('index'))

@app.route('/simulate', methods=['POST'])
def run_simulation():
    try:
        session_data = request.json
        
        # Reconstruct objects from session data
        profile = Profile(**session_data['profile'])
        cash_flows = [RecurringCashFlow(**cf) for cf in session_data['cash_flows']]
        adviser_config = AdviserConfig(**session_data['adviser_config'])
        
        simulator = SimulationService(
            profile=profile,
            cash_flows=cash_flows,
            adviser_config=adviser_config
        )
        
        result = simulator.simulate()
        
        # Convert result to JSON-serializable format
        if hasattr(result, 'model_dump'):
            result_data = result.model_dump()
        else:
            result_data = result
        
        return jsonify({
            'success': True,
            'result': result_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
