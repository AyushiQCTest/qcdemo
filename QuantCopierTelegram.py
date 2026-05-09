import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Setting parameters
bound = 2
max_iterations = 100
colormap = 'nipy_spectral'

# Create the grid of complex numbers
res = 500
x = np.linspace(-2, 1.5, res)
y = np.linspace(-2, 2, res)
X, Y = np.meshgrid(x, y)
C = X + 1j * Y

# Setup the plot
fig, ax = plt.subplots(figsize=(5, 4))
# plt.rc('text', usetex = True) # Disabled as requested
ax.set_aspect('equal')
ax.set_xlabel("Real-Axis")
ax.set_ylabel("Imaginary-Axis")

# Initial plot
mesh = ax.pcolormesh(X, Y, np.zeros_like(X, dtype=int), cmap=colormap, shading='auto', vmin=0, vmax=max_iterations)
colorbar = plt.colorbar(mesh)
title_text = ax.set_title('')

def compute_multibrot_vectorized(power, max_iter=50, escape_bound=2):
    Z = np.zeros_like(C)
    iterations = np.zeros_like(C, dtype=int)
    mask = np.full(C.shape, True, dtype=bool)

    for i in range(max_iter):
        if not mask.any():
            break
        
        # Only update points that haven't escaped yet
        Z[mask] = Z[mask]**power + C[mask]
        
        # Find points that just escaped
        escaped = (np.abs(Z) >= escape_bound) & mask
        
        # update iteration count for escaped points
        iterations[escaped] = i
        
        # Update mask to exclude escaped points from further calculation
        mask[escaped] = False
        
    return iterations

def update(frame):
    # Oscillate power between 1 and 5
    # frame 0->100
    # sin wave or linear? let's do simple linear ping-pong or just 0->4
    # Let's do a smooth transition
    power = 2 + 2 * np.sin(2 * np.pi * frame / 100) # Oscillates between 0 and 4 centered at 2?
    # Wait, power 2 is standard Mandelbrot.
    # Let's go from 0 to 5.
    
    # Simple linear progression for clarity, or oscillation
    # Let's settle on oscillating between 1 and 5 smoothly
    power = 3 + 2 * np.sin(frame / 20) 
    
    iters = compute_multibrot_vectorized(power, max_iterations, bound)
    
    # Update the mesh with flattened data because set_array expects 1D array for QuadMesh depending on mpl version,
    # usually pcolormesh returns a QuadMesh. set_array expects a 1D array of values C.ravel().
    mesh.set_array(iters.ravel())
    title_text.set_text(f'Multibrot set for $z_{{new}} = z^{{{power:.2f}}} + c$')
    return mesh, title_text

# Create animation
# Frames=200, interval=50ms
anim = FuncAnimation(fig, update, frames=np.arange(0, 200), interval=50, blit=False)

plt.show()