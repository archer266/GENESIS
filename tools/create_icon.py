"""Code-native neon cell icon, rendered at high resolution then downsampled."""
from pathlib import Path
import io
import math
import struct
import pygame


def main():
    root = Path(__file__).resolve().parents[1] / "genesis/assets"
    root.mkdir(parents=True, exist_ok=True)
    canvas = pygame.Surface((1024, 1024), pygame.SRCALPHA)
    pygame.draw.rect(canvas, (5, 12, 32), canvas.get_rect(), border_radius=215)
    for x, y, radius, color in ((440, 478, 233, (43, 239, 240)), (740, 735, 103, (255, 78, 171)), (737, 227, 68, (166, 255, 90))):
        glow = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        for r in range(radius+95, radius, -5):
            pygame.draw.circle(glow, (*color, round(25*(1-(r-radius)/100))), (x, y), r)
        canvas.blit(glow, (0, 0))
        membrane = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(membrane, (*color, 55), (x, y), radius)
        pygame.draw.circle(membrane, (*color, 190), (x, y), radius, 6)
        pygame.draw.circle(membrane, (*color, 255), (x-18, y+8), int(radius*.56))
        pygame.draw.arc(membrane, (235, 255, 255, 170), (x-radius+16, y-radius+16, radius*2-32, radius*2-32), .6, 2.4, 8)
        canvas.blit(membrane, (0, 0))
    x,y=246,791
    pygame.draw.polygon(canvas, (255, 210, 94), [(x,y-46),(x+12,y-12),(x+46,y),(x+12,y+12),(x,y+46),(x-12,y+12),(x-46,y),(x-12,y-12)])
    pngs=[]
    for size in (16, 24, 32, 48, 64, 128, 256):
        sprite=pygame.transform.smoothscale(canvas,(size,size))
        stream=io.BytesIO()
        pygame.image.save(sprite,stream,"icon.png")
        pngs.append((size,stream.getvalue()))
        if size==256:
            (root/"genesis.png").write_bytes(stream.getvalue())
    offset=6+16*len(pngs)
    entries=[]
    for size,data in pngs:
        entries.append(struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(data),offset))
        offset+=len(data)
    (root/"genesis.ico").write_bytes(struct.pack('<HHH',0,1,len(pngs))+b''.join(entries)+b''.join(data for _,data in pngs))


if __name__ == "__main__":
    main()
