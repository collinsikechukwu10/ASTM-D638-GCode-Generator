## GCode generator for ASTM D638 Tensile Testing samples.

This generates the gcode of an ASTM D638 sample to be used for tensile testing.
The printed samples are tested to determine examine how microstructure parameters affect the strength of 3d printed builds.

The following parameters can be customized for the sample:
- [x] layer thickness
- [x] layer width
- [x] layer length
- [x] layer raster spacing
- [x] filament size
- [x] sample midsection width
- [x] sample midsection height
- [x] printer type
- [x] nozzle temperature
- [x] bed temperature
- [x] nozzle diameter
- [x] add adhesion
- [x] adhesion layer width
- [x] adhesion layer thickness
- [x] initialization speed
- [x] print speed
- [x] start point (x)
- [x] start point (y)
- [x] sample height

Before running, make sure you install the required libraries
```
python -m pip install -r requirements.txt
```
To start, run the command below
```
streamlit run main.py
```