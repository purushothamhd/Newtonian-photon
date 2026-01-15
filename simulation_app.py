# simulation_app.py

import streamlit as st
import multiprocessing as mp
import subprocess
import time
from physics_engine import simulation_process
from visualizer import visualization_process

def kill_port(port):
    try:
        subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except: pass

st.set_page_config(layout="wide", page_title="Photon-Like Particle Simulator")

st.title("🔬 Photon Collision Simulator")

st.markdown("""
**Features:**
* **Physics:** 2D elastic collisions with momentum and energy conservation
* **Beam Mode:** Fire bursts of photons that interact with existing ones
* **Time Dilation:** Slow down or speed up the simulation
* **Energy Decay:** Simulate energy loss over time
""")

if 'sim_running' not in st.session_state:
    st.session_state.sim_running = False
    st.session_state.q_data = None
    st.session_state.q_param = None
    st.session_state.ps = []

def start():
    kill_port(5006)
    st.session_state.q_data = mp.Queue()
    st.session_state.q_param = mp.Queue()
    p1 = mp.Process(target=simulation_process, args=(st.session_state.q_data, st.session_state.q_param))
    p2 = mp.Process(target=visualization_process, args=(st.session_state.q_data,))
    p1.start(); p2.start()
    st.session_state.ps = [p1, p2]
    st.session_state.q_param.put({'command': 'START'})
    st.session_state.sim_running = True

def stop():
    if st.session_state.q_param: st.session_state.q_param.put({'command': 'STOP'})
    for p in st.session_state.ps:
        if p.is_alive(): p.terminate()
    st.session_state.sim_running = False

col1, col2 = st.columns([1, 2])

with col2:
    st.header("Simulation Parameters")
    
    speed_scale = st.slider("Time Dilation (Speed)", 0.1, 2.0, 1.0, 0.1,
                            help="1.0 = Normal speed. <1.0 = Slow motion.")

    decay = st.slider("Energy Decay per Collision", 0.0, 0.1, 0.00, 0.01, 
                     help="0.0 = Perfect conservation. >0 = Energy loss over time.")
    
    count = st.slider("Photons per Burst", 10, 500, 50, 
                      help="Number of photons to add when firing.")

    if st.button("Apply Parameters", type="secondary"):
        if st.session_state.sim_running:
            st.session_state.q_param.put({'params': {
                'photon_count': count,
                'global_decay': decay,
                'time_scale': speed_scale
            }})
            st.toast("✓ Parameters Updated")

with col1:
    st.header("Controls")
    if st.button("▶️ Start Simulation", disabled=st.session_state.sim_running, use_container_width=True):
        start(); st.rerun()
        
    if st.button("🔥 Fire Photon Beam", disabled=not st.session_state.sim_running, type="primary", use_container_width=True):
        st.session_state.q_param.put({'params': {
            'photon_count': count,
            'time_scale': speed_scale
        }}) 
        st.session_state.q_param.put({'command': 'FIRE'})
        
    if st.button("🗑️ Clear All Photons", disabled=not st.session_state.sim_running, use_container_width=True):
        st.session_state.q_param.put({'command': 'CLEAR'})

    if st.button("⏹️ Stop Simulation", disabled=not st.session_state.sim_running, use_container_width=True):
        stop(); st.rerun()

    if st.session_state.sim_running:
        st.success("🟢 Engine Running")
        st.markdown("[Open Visualizer](http://localhost:5006)")
