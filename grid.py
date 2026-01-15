# grid.py

class Grid:
    def __init__(self, bounds, cell_size):
        self.bounds = bounds
        self.cell_size = float(cell_size)
        self.cells = {}

    def clear(self):
        self.cells = {}

    def insert(self, particle):
        x = int(particle.position.x / self.cell_size)
        y = int(particle.position.y / self.cell_size)
        key = (x, y)
        if key not in self.cells:
            self.cells[key] = []
        self.cells[key].append(particle)

    def get_neighbors(self, particle):
        cx = int(particle.position.x / self.cell_size)
        cy = int(particle.position.y / self.cell_size)
        neighbors = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                key = (cx + dx, cy + dy)
                if key in self.cells:
                    neighbors.extend(self.cells[key])
        return neighbors
