# used for debugging

import pygame
import json

ISLANDS_PATH = "./shapez2/gameFiles/islands.json"

with open(ISLANDS_PATH) as f:
    islands = json.load(f)

buildable = []

print()
print("Islands without a buildable area :")

for i in islands["Islands"]:
    if all(c["BuildableTiles"] == [] for c in i["Chunks"]):
        print(i["Id"])
    else:
        buildable.append(i)

print()
input("Press enter to continue")

for island in buildable:

    chunks = island["Chunks"]
    minLayer = min(c["Pos"]["z"] for c in chunks)
    tiles:list[tuple[int,int,int]] = []

    for c in chunks:
        rawTiles = sum((list(range(r[0],r[1]+1,r[2])) for r in c["BuildableTiles"]),start=[])
        for t in rawTiles:
            y, x = divmod(t,20)
            tiles.append((
                x + (c["Pos"]["x"]*20),
                y + (c["Pos"]["y"]*20),
                c["Pos"]["z"] - minLayer
            ))
            assert 0 <= tiles[-1][2] <= 2

    minX = min(t[0] for t in tiles)
    minY = min(t[1] for t in tiles)
    maxX = max(t[0] for t in tiles)
    maxY = max(t[1] for t in tiles)
    width = maxX - minX + 1
    height = maxY - minY + 1
    winHeight = 300
    winWidth = round((width*winHeight)/height)
    cellSize = winHeight / height

    surf = pygame.Surface((winWidth,winHeight))
    for x in range(minX,maxX+1):
        for y in range(minY,maxY+1):
            color = tuple(255 if (x,y,z) in tiles else 0 for z in range(3))
            left = (x-minX) * cellSize
            top = (y-minY) * cellSize
            pygame.draw.rect(surf,color,pygame.Rect(left,top,cellSize,cellSize))
            pygame.draw.rect(surf,(127,127,127),pygame.Rect(left,top,cellSize,cellSize),round(cellSize/10))

    win = pygame.display.set_mode((winWidth,winHeight))
    pygame.display.set_caption(island["Id"])
    win.blit(surf,(0,0))
    pygame.display.update()
    clock = pygame.time.Clock()
    run = True
    while run:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break
    pygame.display.quit()