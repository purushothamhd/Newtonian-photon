# visualizer.py

import sys
import signal
import queue
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Div
from bokeh.layouts import column
from bokeh.server.server import Server

def wavelength_to_hex(wavelength):
    """Convert wavelength to RGB hex color (visible + invisible spectrums)"""
    w = float(wavelength)
    
    # --- VISUALIZE INVISIBLE SPECTRUMS ---
    if w < 380:  # UV
        return "#C0C0FF"  # Light violet/blue tint (higher energy)
    if w > 750:  # IR
        return "#404040"  # Dark grey (lower energy, invisible)

    # --- STANDARD VISIBLE SPECTRUM ---
    R, G, B = 0.0, 0.0, 0.0
    
    if 380 <= w < 440:
        R = -(w - 440) / (440 - 380)
        B = 1.0
    elif 440 <= w < 490:
        G = (w - 440) / (490 - 440)
        B = 1.0
    elif 490 <= w < 510:
        G = 1.0
        B = -(w - 510) / (510 - 490)
    elif 510 <= w < 580:
        R = (w - 510) / (580 - 510)
        G = 1.0
    elif 580 <= w < 645:
        R = 1.0
        G = -(w - 645) / (645 - 580)
    elif 645 <= w <= 750:
        R = 1.0
    
    # Intensity falloff at edges
    if 380 <= w < 420:
        factor = 0.3 + 0.7 * (w - 380) / (420 - 380)
    elif 420 <= w < 701:
        factor = 1.0
    elif 701 <= w <= 750:
        factor = 0.3 + 0.7 * (750 - w) / (750 - 700)
    else:
        factor = 0.3

    gamma = 0.8
    def adjust(color, factor):
        return int(255 * (color * factor) ** gamma)

    return f"#{adjust(R, factor):02x}{adjust(G, factor):02x}{adjust(B, factor):02x}"

def visualization_process(data_q):
    """Bokeh visualization server"""
    server = None
    
    def cleanup(signum=None, frame=None):
        if server:
            try:
                server.stop()
            except:
                pass
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    def bokeh_app(doc):
        # Data source
        source = ColumnDataSource(data={'x': [], 'y': [], 'color': []})
        
        # Info display
        info_div = Div(text="""
        <div style="padding: 10px; background: #1a1a1a; border-radius: 5px; color: #fff;">
            <h3 style="color: #4fc3f7; margin-top: 0;">🔬 Photon Collision Simulator</h3>
            <p style="margin: 5px 0; font-size: 12px;">
                <strong>Particles:</strong> <span id="particle_count">0</span> | 
                <strong>Total Energy:</strong> <span id="total_energy">0</span> | 
                <strong>Collisions:</strong> <span id="collision_count">0</span>
            </p>
        </div>
        """, width=780, height=80)

        # Main plot
        p = figure(
            width=800, height=600,
            title="Photon Collision Dynamics (Color = Wavelength)",
            x_range=(0, 800), y_range=(0, 600),
            background_fill_color="#0a0a0a",
            tools="pan,wheel_zoom,reset,save"
        )
        
        # Styling
        p.title.text_color = "#ffffff"
        p.title.text_font_size = "14pt"
        p.grid.visible = False
        p.axis.visible = False
        p.border_fill_color = "#1a1a1a"
        p.outline_line_color = "#333333"

        # Particle renderer
        p.scatter(
            x='x', y='y',
            size=11,
            color='color',
            source=source,
            line_color="white",
            line_width=0.8,
            line_alpha=0.5,
            alpha=0.95
        )

        def update():
            """Update visualization from physics data"""
            try:
                data = None
                # Get most recent frame
                while not data_q.empty():
                    data = data_q.get_nowait()
                
                if data and 'frame' in data:
                    frame = data['frame']
                    
                    # Convert wavelengths to colors
                    hex_colors = [wavelength_to_hex(w) for w in frame['wavelength']]
                    
                    # Update particle positions
                    source.data = {
                        'x': frame['x'],
                        'y': frame['y'],
                        'color': hex_colors
                    }
                    
                    # Update statistics in info div
                    total_energy = frame.get('total_energy', 0)
                    collision_count = frame.get('collisions', 0)
                    
                    info_div.text = f"""
                    <div style="padding: 10px; background: #1a1a1a; border-radius: 5px; color: #fff;">
                        <h3 style="color: #4fc3f7; margin-top: 0;">🔬 Photon Collision Simulator</h3>
                        <p style="margin: 5px 0; font-size: 12px;">
                            <strong>Particles:</strong> {frame['count']} | 
                            <strong>Total Energy:</strong> {total_energy:.1f} | 
                            <strong>Collisions:</strong> {collision_count}
                        </p>
                    </div>
                    """
            except:
                pass

        # Add periodic callback
        doc.add_periodic_callback(update, 50)  # 20 FPS display
        
        # Layout
        layout = column(info_div, p)
        doc.add_root(layout)

    try:
        server = Server({'/': bokeh_app}, port=5006, allow_websocket_origin=["*"])
        server.start()
        print("Visualization server running at http://localhost:5006")
        server.io_loop.start()
    except Exception as e:
        print(f"Server error: {e}")
        cleanup()
