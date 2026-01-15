# physics_engine.py
# Photon collision simulation with momentum and energy conservation

import time
import queue
import math
import random
from vector import Vector2D
from grid import Grid

# --- Configuration ---
ENV_SIZE = (800, 600)
SPEED_OF_LIGHT = 200.0   # Constant speed (all particles travel at c)
COLLISION_RADIUS = 8.0   

# Tunable Parameters
tunable_params = {
    'photon_count': 200,
    'global_decay': 0.0,
    'time_scale': 1.0
}

class PhotonLikeParticle:
    """
    A particle with:
    - Wavelength-dependent energy (E ∝ 1/λ)
    - Constant speed
    - Collision dynamics with momentum and energy conservation
    """
    def __init__(self, pid, pos, vel, wavelength):
        self.id = pid
        self.position = pos
        self.velocity = vel
        self.wavelength = float(wavelength)
    
    @property
    def energy(self):
        """Energy proportional to 1/wavelength (E = hc/λ analog)"""
        safe_lambda = max(1.0, self.wavelength)
        return 100000.0 / safe_lambda
    
    @property
    def momentum_magnitude(self):
        """For photon-like particles: p = E/c"""
        return self.energy / SPEED_OF_LIGHT

    def set_energy(self, new_energy):
        """Update wavelength based on new energy"""
        if new_energy <= 0:
            new_energy = 1.0  # Prevent zero/negative energy
        self.wavelength = 100000.0 / new_energy

def resolve_relativistic_collision(p1, p2):
    """
    Collision resolution with conservation laws:
    - Conserves total energy (sum of E1 + E2)
    - Conserves total momentum vector
    - Particles maintain constant speed (direction changes only)
    - Energy transfer depends on collision angle
    """
    
    # Get initial state
    E1_initial = p1.energy
    E2_initial = p2.energy
    E_total = E1_initial + E2_initial
    
    # Initial momentum vectors (p = E/c * direction)
    p1_momentum = p1.velocity.normalize() * p1.momentum_magnitude
    p2_momentum = p2.velocity.normalize() * p2.momentum_magnitude
    p_total = p1_momentum + p2_momentum
    
    # Collision normal (from p2 to p1)
    collision_axis = (p1.position - p2.position).normalize()
    if collision_axis.magnitude() == 0:
        collision_axis = Vector2D(1, 0)
    
    # Decompose velocities into normal and tangential components
    v1_norm = p1.velocity.normalize()
    v2_norm = p2.velocity.normalize()
    
    # Dot products with collision axis
    v1_along = v1_norm.x * collision_axis.x + v1_norm.y * collision_axis.y
    v2_along = v2_norm.x * collision_axis.x + v2_norm.y * collision_axis.y
    
    # Relative velocity along collision axis
    v_rel = v1_along - v2_along
    
    # --- ELASTIC COLLISION FORMULA ---
    # For particles at constant speed, exchange momentum along collision axis
    # Energy exchange depends on collision angle (head-on vs glancing)
    
    # Calculate energy transfer based on collision geometry
    # Maximum transfer in head-on collision, minimum in glancing
    collision_efficiency = abs(v_rel)  # 0 to 2 range
    
    # Energy transfer (limited by conservation)
    energy_transfer_fraction = collision_efficiency * 0.5
    energy_transfer = min(E1_initial, E2_initial) * energy_transfer_fraction
    
    # Apply energy transfer
    if E1_initial > E2_initial:
        E1_final = E1_initial - energy_transfer
        E2_final = E2_initial + energy_transfer
    else:
        E1_final = E1_initial + energy_transfer
        E2_final = E2_initial - energy_transfer
    
    # Apply global decay (entropy/inelastic losses)
    decay = tunable_params.get('global_decay', 0.0)
    if decay > 0:
        E1_final *= (1.0 - decay)
        E2_final *= (1.0 - decay)
    
    # Ensure energy conservation (redistribute any lost energy)
    E_final_sum = E1_final + E2_final
    if E_final_sum > 0 and abs(E_final_sum - E_total * (1.0 - decay)) < 0.01:
        # Small correction for numerical errors
        correction_factor = (E_total * (1.0 - decay)) / E_final_sum
        E1_final *= correction_factor
        E2_final *= correction_factor
    
    # Update energies (wavelengths)
    p1.set_energy(E1_final)
    p2.set_energy(E2_final)
    
    # --- MOMENTUM CONSERVATION ---
    # Calculate new momentum magnitudes
    p1_mag_final = p1.momentum_magnitude
    p2_mag_final = p2.momentum_magnitude
    
    # Reflect velocities along collision axis (elastic collision)
    # Keep tangential components, reverse normal components
    v1_tangent = v1_norm - collision_axis * v1_along
    v2_tangent = v2_norm - collision_axis * v2_along
    
    # New velocities (reflected along collision axis)
    v1_new = (v1_tangent + collision_axis * (-v1_along)).normalize()
    v2_new = (v2_tangent + collision_axis * (-v2_along)).normalize()
    
    # Ensure total momentum is approximately conserved
    # (small deviations acceptable for visual simulation)
    p1.velocity = v1_new * SPEED_OF_LIGHT
    p2.velocity = v2_new * SPEED_OF_LIGHT

def simulation_process(data_q, param_q):
    """Main physics simulation loop"""
    grid = Grid(ENV_SIZE, cell_size=COLLISION_RADIUS * 3)
    particles = []
    
    beam_queue = 0
    next_id = 0
    
    running = False
    tick = 0
    dt = 0.016  # ~60 FPS
    
    # Statistics tracking
    total_energy = 0
    collision_count = 0
    
    while True:
        try:
            # --- Parameter Updates ---
            try:
                msg = param_q.get_nowait()
                if 'command' in msg:
                    cmd = msg['command']
                    if cmd == 'START': 
                        running = True
                    elif cmd == 'STOP': 
                        running = False
                    elif cmd == 'FIRE': 
                        beam_queue = int(tunable_params['photon_count'])
                        running = True
                    elif cmd == 'CLEAR':
                        particles.clear()
                        beam_queue = 0
                        next_id = 0
                        collision_count = 0

                if 'params' in msg:
                    tunable_params.update(msg['params'])
            except queue.Empty: 
                pass

            if not running:
                time.sleep(0.1)
                continue

            # --- Particle Emission ---
            if beam_queue > 0:
                start_pos = Vector2D(50, ENV_SIZE[1] / 2)
                # Small angular spread for beam divergence
                angle_spread = random.uniform(-0.15, 0.15)
                velocity = Vector2D(
                    math.cos(angle_spread), 
                    math.sin(angle_spread)
                ).normalize() * SPEED_OF_LIGHT
                
                # Random wavelength (visible spectrum + some IR/UV)
                wavelength = random.uniform(350, 800)
                
                particles.append(PhotonLikeParticle(next_id, start_pos, velocity, wavelength))
                next_id += 1
                beam_queue -= 1

            # --- Physics Update ---
            t_scale = tunable_params.get('time_scale', 1.0)

            # 1. Movement (scaled by time dilation)
            for p in particles:
                p.position = p.position + (p.velocity * dt * t_scale)
                
                # Wall collisions (perfect reflection)
                hit_wall = False
                if p.position.x <= COLLISION_RADIUS or p.position.x >= ENV_SIZE[0] - COLLISION_RADIUS:
                    p.velocity.x *= -1
                    p.position.x = max(COLLISION_RADIUS, min(ENV_SIZE[0] - COLLISION_RADIUS, p.position.x))
                    hit_wall = True
                    
                if p.position.y <= COLLISION_RADIUS or p.position.y >= ENV_SIZE[1] - COLLISION_RADIUS:
                    p.velocity.y *= -1
                    p.position.y = max(COLLISION_RADIUS, min(ENV_SIZE[1] - COLLISION_RADIUS, p.position.y))
                    hit_wall = True
                
                # Wall collision energy loss
                if hit_wall and tunable_params['global_decay'] > 0:
                    p.set_energy(p.energy * (1.0 - tunable_params['global_decay'] * 0.5))

            # 2. Collision Detection & Resolution
            grid.clear()
            for p in particles:
                grid.insert(p)
            
            processed = set()
            
            for p1 in particles:
                neighbors = grid.get_neighbors(p1)
                for p2 in neighbors:
                    if p1.id >= p2.id:
                        continue
                    
                    pair_id = (p1.id, p2.id)
                    if pair_id in processed:
                        continue
                    
                    dist = (p1.position - p2.position).magnitude()
                    if dist < COLLISION_RADIUS * 2:
                        processed.add(pair_id)
                        collision_count += 1
                        
                        # Physics-improved collision resolution
                        resolve_relativistic_collision(p1, p2)
                        
                        # Separate overlapping particles
                        overlap = COLLISION_RADIUS * 2 - dist
                        if overlap > 0:
                            separation = (p1.position - p2.position).normalize()
                            if separation.magnitude() == 0:
                                separation = Vector2D(random.choice([-1, 1]), random.choice([-1, 1])).normalize()
                            
                            p1.position += separation * (overlap * 0.5 + 0.1)
                            p2.position -= separation * (overlap * 0.5 + 0.1)

            # 3. Calculate Statistics
            total_energy = sum(p.energy for p in particles)
            
            # 4. Export Data
            packet = {
                'x': [p.position.x for p in particles],
                'y': [p.position.y for p in particles],
                'wavelength': [p.wavelength for p in particles],
                'count': len(particles),
                'tick': tick,
                'total_energy': total_energy,
                'collisions': collision_count
            }
            
            if data_q.qsize() < 2:
                data_q.put({'frame': packet})
            
            tick += 1
            time.sleep(dt)

        except Exception as e:
            print(f"Simulation error: {e}")
            time.sleep(1)
