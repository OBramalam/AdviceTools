# Financial Simulation UI

A web interface for the Financial Simulation Tool that allows users to upload conversation files and run retirement simulations.

## Features

- **File Upload**: Drag & drop or click to upload conversation files
- **Profile Extraction**: Automatically extracts financial profile from conversations
- **Simulation Engine**: Runs Monte Carlo simulations for retirement planning
- **Results Visualization**: Displays simulation results with charts and insights

## Setup

1. Install dependencies:
```bash
cd ui
pip install -r requirements.txt
```

2. Run the application:
```bash
python run.py
```

3. Open your browser and go to: http://localhost:5000

## Usage

1. **Upload**: Upload a .txt file containing your financial conversation
2. **Review**: Review the extracted profile and cash flows
3. **Simulate**: Click "Run Simulation" to generate retirement projections
4. **Analyze**: View the results and insights

## File Structure

```
ui/
├── app.py              # Flask application
├── run.py              # Simple runner script
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   ├── base.html       # Base template
│   ├── index.html      # Upload page
│   └── simulation.html # Results page
└── uploads/            # Uploaded files (created automatically)
```

## Dependencies

- Flask: Web framework
- Bootstrap 5: UI styling
- Chart.js: Data visualization
- Font Awesome: Icons

## Notes

- The UI requires the main simulation engine to be in the parent directory
- Uploaded files are stored in the `uploads/` directory
- The application runs in debug mode by default
