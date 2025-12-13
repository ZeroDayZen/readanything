#!/usr/bin/env python3
"""
Script to create logo for ReadAnything app
Creates PNG logo files in various sizes
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    import math
except ImportError:
    print("Pillow is required. Install with: pip install Pillow")
    exit(1)

def create_logo(size=512):
    """Create a minimalist speech bubble with audio waveform logo"""
    # Create image with light grey background
    bg_color = (245, 245, 245, 255)  # Light grey background
    img = Image.new('RGBA', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Colors
    bubble_color = (60, 60, 60, 255)  # Dark grey/charcoal for speech bubble
    waveform_color = (255, 255, 255, 255)  # White for waveform
    
    center_x = size / 2
    center_y = size / 2
    
    # Speech bubble dimensions
    bubble_width = size * 0.65
    bubble_height = size * 0.5
    bubble_x = center_x - bubble_width / 2
    bubble_y = center_y - bubble_height / 2 - size * 0.05
    
    # Draw speech bubble (rounded rectangle with tail)
    # Main body of bubble
    bubble_radius = size * 0.08
    bubble_rect = [
        bubble_x,
        bubble_y,
        bubble_x + bubble_width,
        bubble_y + bubble_height
    ]
    draw.rounded_rectangle(bubble_rect, radius=bubble_radius, fill=bubble_color)
    
    # Draw tail/pointer on bottom-left
    tail_size = size * 0.08
    tail_points = [
        (bubble_x + size * 0.12, bubble_y + bubble_height),  # Top of tail
        (bubble_x + size * 0.05, bubble_y + bubble_height + tail_size),  # Point
        (bubble_x + size * 0.18, bubble_y + bubble_height)  # Bottom of tail
    ]
    draw.polygon(tail_points, fill=bubble_color)
    
    # Draw audio waveform inside the bubble
    # Waveform starts small on left, peaks in center, diminishes on right
    waveform_margin = size * 0.12
    waveform_x_start = bubble_x + waveform_margin
    waveform_x_end = bubble_x + bubble_width - waveform_margin
    waveform_y_center = bubble_y + bubble_height / 2
    waveform_width = waveform_x_end - waveform_x_start
    waveform_height = size * 0.2  # Max amplitude
    
    # Create waveform points - more pronounced peaks in center
    num_points = 80
    points = []
    for i in range(num_points + 1):
        x = waveform_x_start + (i / num_points) * waveform_width
        # Create waveform: small on left, tall peaks in center, small on right
        progress = i / num_points  # 0 to 1
        
        # Amplitude envelope: small -> large -> small
        if progress < 0.25:
            # Start small and grow
            amplitude = 0.15 + (progress / 0.25) * 0.85
        elif progress < 0.75:
            # Full amplitude in center
            amplitude = 1.0
        else:
            # Diminish on right
            amplitude = 1.0 - ((progress - 0.75) / 0.25) * 0.85
        
        # Create wave pattern with sharp peaks and deep troughs
        # Multiple sine waves for complex waveform
        wave1 = math.sin(progress * math.pi * 10) * amplitude
        wave2 = math.sin(progress * math.pi * 15) * amplitude * 0.4
        wave3 = math.sin(progress * math.pi * 20) * amplitude * 0.2
        wave_value = wave1 + wave2 + wave3
        
        y = waveform_y_center + wave_value * waveform_height / 2
        points.append((x, y))
    
    # Draw waveform line with thicker stroke for visibility
    if len(points) > 1:
        stroke_width = max(2, int(size * 0.025))
        draw.line(points, fill=waveform_color, width=stroke_width)
    
    return img

def main():
    """Generate logo files in various sizes"""
    sizes = {
        'logo_512.png': 512,
        'logo_256.png': 256,
        'logo_128.png': 128,
        'logo_64.png': 64,
        'logo_32.png': 32,
        'logo_16.png': 16
    }
    
    print("Creating minimalist speech bubble logo...")
    for filename, size in sizes.items():
        logo = create_logo(size)
        logo.save(filename, 'PNG')
        print(f"Created {filename} ({size}x{size})")
    
    print("\nLogo files created successfully!")

if __name__ == "__main__":
    main()
