import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import random
import sys
import time
import math

WIDTH, HEIGHT = 800, 800
SPEED = 0.02
INTERSECTION_BOUNDARY = 0.1
LANE_OFFSET = 0.1  # Lateral offset for left-hand traffic lane

# Traffic Directions
DIRECTIONS = ['N', 'S', 'E', 'W']
signal_index = 0
signal_timer = time.time()
SIGNAL_INTERVAL = 6

# Vehicle queues
vehicles = {d: [] for d in DIRECTIONS}

# Texture globals
car_texture = None
road_texture = None


def load_texture(path):
    surface = pygame.image.load(path)
    texture_data = pygame.image.tostring(surface, "RGBA", 1)
    width, height = surface.get_size()

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    return texture_id


class Vehicle:
    def __init__(self, direction):
        self.initial_direction = direction
        self.direction = direction
        self.size = 0.1
        self.state = 'approach'
        self.passed_center = False
        self.color = random.choice([(1, 0, 0), (0, 1, 0), (0, 0.3, 1), (1, 0.5, 0)])
        if direction == 'N':
            self.x, self.y = -LANE_OFFSET, -1.1
            self.dx, self.dy = 0, SPEED
        elif direction == 'S':
            self.x, self.y = LANE_OFFSET, 1.1
            self.dx, self.dy = 0, -SPEED
        elif direction == 'E':
            self.x, self.y = 1.1, LANE_OFFSET
            self.dx, self.dy = -SPEED, 0
        else:
            self.x, self.y = -1.1, -LANE_OFFSET
            self.dx, self.dy = SPEED, 0

    def update(self, is_green, others):
        global vehicles
        spacing = 0.12
        idx = others.index(self)
        if self.direction == 'N': base = -0.15
        elif self.direction == 'S': base = 0.15
        elif self.direction == 'E': base = 0.15
        else: base = -0.15
        desired_stop = base + (-idx if self.direction in ['N', 'W'] else idx) * (self.size + spacing)
        ahead = None
        for v in others:
            if v == self: break
            ahead = v
        stop = False
        if not self.state == 'depart' and not is_green:
            if self.direction == 'N' and self.y + self.size >= desired_stop: stop = True
            if self.direction == 'S' and self.y - self.size <= desired_stop: stop = True
            if self.direction == 'E' and self.x - self.size <= desired_stop: stop = True
            if self.direction == 'W' and self.x + self.size >= desired_stop: stop = True
        if ahead:
            if self.direction in ['N', 'S'] and abs(ahead.y - self.y) < spacing: stop = True
            if self.direction in ['E', 'W'] and abs(ahead.x - self.x) < spacing: stop = True
        if not stop and self.state == 'approach' and is_green:
            nx, ny = self.x + self.dx, self.y + self.dy
            if abs(nx) < INTERSECTION_BOUNDARY and abs(ny) < INTERSECTION_BOUNDARY:
                perp = ['E', 'W'] if self.direction in ['N', 'S'] else ['N', 'S']
                for d in perp:
                    for v in vehicles[d]:
                        if abs(v.x) < INTERSECTION_BOUNDARY and abs(v.y) < INTERSECTION_BOUNDARY:
                            stop = True; break
                    if stop: break
        if stop: return
        if self.state == 'approach':
            self.x += self.dx; self.y += self.dy
            if (self.direction in ['N', 'S'] and abs(self.y) < 0.01) or (self.direction in ['E', 'W'] and abs(self.x) < 0.01):
                self.passed_center = True
                self.state = 'depart'
        else:
            self.x += self.dx; self.y += self.dy

    def draw(self):
        if car_texture:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, car_texture)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(self.x - self.size / 2, self.y - self.size / 2)
            glTexCoord2f(1, 0); glVertex2f(self.x + self.size / 2, self.y - self.size / 2)
            glTexCoord2f(1, 1); glVertex2f(self.x + self.size / 2, self.y + self.size / 2)
            glTexCoord2f(0, 1); glVertex2f(self.x - self.size / 2, self.y + self.size / 2)
            glEnd()
            glDisable(GL_TEXTURE_2D)
        else:
            glColor3f(*self.color)
            glBegin(GL_QUADS)
            glVertex2f(self.x - self.size / 2, self.y - self.size / 2)
            glVertex2f(self.x + self.size / 2, self.y - self.size / 2)
            glVertex2f(self.x + self.size / 2, self.y + self.size / 2)
            glVertex2f(self.x - self.size / 2, self.y + self.size / 2)
            glEnd()


def draw_road():
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    # Vertical road
    glVertex2f(-0.15, -1.0)
    glVertex2f(0.15, -1.0)
    glVertex2f(0.15, 1.0)
    glVertex2f(-0.15, 1.0)
    # Horizontal road
    glVertex2f(-1.0, -0.15)
    glVertex2f(1.0, -0.15)
    glVertex2f(1.0, 0.15)
    glVertex2f(-1.0, 0.15)
    glEnd()



def draw_signal_circle(x, y, is_green):
    glColor3f(0, 1, 0) if is_green else glColor3f(1, 0, 0)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(x, y)
    for angle in range(0, 361, 10):
        rad = math.radians(angle)
        glVertex2f(x + 0.025 * math.cos(rad), y + 0.025 * math.sin(rad))
    glEnd()


def draw_signals():
    for idx, direction in enumerate(DIRECTIONS):
        is_green = (idx == signal_index)
        if direction == 'N': draw_signal_circle(0.225, 0.55, is_green)
        elif direction == 'S': draw_signal_circle(-0.225, -0.55, is_green)
        elif direction == 'E': draw_signal_circle(-0.5, 0.275, is_green)
        elif direction == 'W': draw_signal_circle(0.5, -0.275, is_green)

def spawn_vehicle():
    dir_choice = random.choice(DIRECTIONS)
    vehicles[dir_choice].append(Vehicle(dir_choice))


def main():
    global signal_index, signal_timer, car_textures
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF|OPENGL)
    gluOrtho2D(-1,1,-1,1)
    clock = pygame.time.Clock()

    # load car textures
    car_textures = [
        load_texture("car-truck1.png"),
        load_texture("car-truck2.png"),
        load_texture("car-truck4.png"),
        load_texture("car-truck5.png"),
    ]

    spawn_timer = time.time()
    running = True
    while running:
        glClear(GL_COLOR_BUFFER_BIT)
        draw_road(); draw_signals()

        current = time.time()
        if current - signal_timer > SIGNAL_INTERVAL:
            signal_index = (signal_index+1)%4; signal_timer=current
        if current - spawn_timer > 2:
            spawn_vehicle(); spawn_timer=current

        for idx, d in enumerate(DIRECTIONS):
            green = (idx==signal_index)
            for v in vehicles[d]:
                v.update(green, vehicles[d]); v.draw()
            vehicles[d] = [v for v in vehicles[d] if -1.2<v.x<1.2 and -1.2<v.y<1.2]

        pygame.display.flip(); clock.tick(60)
        for e in pygame.event.get():
            if e.type==pygame.QUIT: running=False
    pygame.quit(); sys.exit()

if __name__=='__main__': main()