import fitz  # PyMuPDF
from pathlib import Path

def create_sample_ac450_pdf(output_path: Path):
    """
    Creates a realistic synthetic PDF simulating ABB AC450 Database Element printouts
    with complementary hardware/software default blocks, *** END OF DEFAULTS *** markers,
    and page header/footer metadata.
    """
    doc = fitz.open()
    
    # Page 1: AI (DEFAULT AI + DEFAULT AIS) & AO (DEFAULT AO + DEFAULT AOS)
    page1 = doc.new_page()
    text1 = """
ABB Automation                         DATABASE LISTING                        Sheet 108
Prepared: J. Doe                       Approved: M. Smith                      Cont. 109
Document Number: 3BSE008543R101        Revision: B                             Date: 2026-07-21
Copyright (c) ABB Automation Inc. All rights reserved.

================================================================================
DEFAULT AI
================================================================================
  :TYPE ANALOG_INPUT
  :SERVICE YES
  :SCANT 1s
  :CONV_PAR 0
  :IMPL 1

DEFAULT AIS
================================================================================
  :UNIT %
  :RANGEMAX 100.000
  :RANGEMIN -100.000
  :DEC 2
  :ERR_TR 0
  :CLASS 0
  :DESCR

*** END OF DEFAULTS ***

AI1.1
  :NAME "BOILER_PRESS_TR_01"
  :DESCR "Boiler Steam Drum Pressure"
  :UNIT "BAR"
  :RANGEMAX 150.000
  :RANGEMIN 0.000
  :ACTUAL 84.5

AI1.2
  :NAME "FEEDWATER_FLOW_01"
  :DESCR "Boiler Feedwater Inlet Flow Rate"
  :UNIT "M3/H"
  :RANGEMAX 500.000
  :RANGEMIN 0.000
  :ACTUAL 320.0

================================================================================
DEFAULT AO
================================================================================
  :TYPE OUTPUT_4_20MA
  :SERVICE YES
  :CONV_PAR 1

DEFAULT AOS
================================================================================
  :UNIT %
  :RANGEMAX 100.000
  :RANGEMIN 0.000
  :DEC 2

*** END OF DEFAULTS ***

AO2.1
  :NAME "STEAM_VALVE_OUT_01"
  :DESCR "Main Steam Control Valve Position Demand"
  :RANGEMAX 100.0
  :ACTUAL 62.4

AO2.2
  :NAME "FEEDWATER_PUMP_SPEED"
  :DESCR "Feedwater VFD Speed Setpoint Output"
  :UNIT "RPM"
  :RANGEMAX 3000.0
  :ACTUAL 2450.0
"""
    page1.insert_text((40, 40), text1, fontsize=9, fontname="Courier")

    # Page 2: PIDCON, MOTCON, VALVECON, DS, DAT, TEXT
    page2 = doc.new_page()
    text2 = """
ABB Automation                         DATABASE LISTING                        Sheet 109
Prepared: J. Doe                       Approved: M. Smith                      Cont. 110
Document Number: 3BSE008543R101        Revision: B                             Date: 2026-07-21

================================================================================
DEFAULT PIDCON
================================================================================
  :GAIN 1.0
  :TI 30.0
  :TD 0.0
  :SP 50.0
  :MODE AUTO
  :ACT 1
  :DEC 2

*** END OF DEFAULTS ***

PIDCON1
  :NAME "DRUM_PRESS_CTRL"
  :DESCR "Steam Drum Pressure PID Controller"
  :GAIN 2.5
  :TI 45.0
  :SP 85.0
  :PV 84.5
  :OUT 62.4

================================================================================
DEFAULT MOTCON
================================================================================
  :TRIP FALSE
  :RUNNING FALSE
  :CURRENT 0.0
  :COMMAND STOP
  :UNIT A

*** END OF DEFAULTS ***

MOTCON1
  :NAME "MAIN_PUMP_M01"
  :DESCR "High Pressure Boiler Feed Pump Motor"
  :RUNNING TRUE
  :CURRENT 142.5
  :COMMAND "START"

================================================================================
DEFAULT VALVECON
================================================================================
  :OPEN FALSE
  :CLOSED TRUE
  :FAULT FALSE
  :POSITION 0.0

*** END OF DEFAULTS ***

VALVECON1
  :NAME "EMERGENCY_VENT_V01"
  :DESCR "Emergency Safety Vent Valve"
  :OPEN TRUE
  :CLOSED FALSE
  :POSITION 100.0

DS1
  :NAME "PLANT_STATUS_FLAG"
  :DESCR "Overall Plant Operational State"
  :VALUE "NORMAL_OPERATION"

DAT1
  :NAME "CYCLE_TIME_MS"
  :DESCR "Controller Task Cycle Duration"
  :VALUE 50

TEXT1
  :NAME "HEADER_NOTE_01"
  :DESCR "System revision 4.2 configuration load"
"""
    page2.insert_text((40, 40), text2, fontsize=9, fontname="Courier")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    doc.close()
    print(f"Realistic multi-block sample AC450 DB PDF created at: {output_path}")

if __name__ == "__main__":
    sample_pdf_path = Path(__file__).parent / "sample_ac450_db.pdf"
    create_sample_ac450_pdf(sample_pdf_path)
