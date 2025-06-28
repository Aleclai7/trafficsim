import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import random
import sys
import time
import math
from PIL import Image

WIDTH, HEIGHT = 800, 800
BASE_SPEED = 0.02
INTERSECTION_BOUNDARY = 0.15
LANE_OFFSET = 0.12
SIGNAL_INTERVAL = 6
DIRECTIONS = ['N', 'S', 'E', 'W']

vehicles = {d: [] for d in DIRECTIONS}
signal_index = 0
signal_timer = time.time()
spawn_timer = time.time()
car_textures = []
car_aspect_ratios = []

DIRECTION_CONFIG = {
    'N': {'pos': (-LANE_OFFSET, -1.2), 'vel': (0, BASE_SPEED), 'stop_base': -0.25},
    'S': {'pos': (LANE_OFFSET, 1.2), 'vel': (0, -BASE_SPEED), 'stop_base': 0.25},
    'E': {'pos': (1.2, -LANE_OFFSET), 'vel': (-BASE_SPEED, 0), 'stop_base': 0.25},
    'W': {'pos': (-1.2, LANE_OFFSET), 'vel': (BASE_SPEED, 0), 'stop_base': -0.25}
}

SIGNAL_POSITIONS = {
    'N': (0.27, 0.65),
    'S': (-0.27, -0.65),
    'E': (-0.65, 0.27),
    'W': (0.65, -0.27)
}

DIRECTION_ARROWS = {
    'N': '↑',
    'S': '↓',
    'E': '→',
    'W': '←'
}

def load_texture_with_aspect(path):
    surface = pygame.image.load(path)
    texture_data = pygame.image.tostring(surface, "RGBA", 1)
    width, height = surface.get_size()
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return tex_id, width / height

class Vehicle:
    def __init__(self, direction):
        cfg = DIRECTION_CONFIG[direction]
        self.direction = direction
        self.x, self.y = cfg['pos']
        self.dx, self.dy = cfg['vel']
        self.speed = BASE_SPEED * random.uniform(0.85, 1.15)
        idx = random.randint(0, len(car_textures) - 1)
        self.texture = car_textures[idx]
        self.aspect_ratio = car_aspect_ratios[idx]
        self.size = 0.12
        self.state = 'approach'
        self.passed_center = False

    def update(self, is_green, others):
        idx = others.index(self)
        spacing = 0.18
        stop_base = DIRECTION_CONFIG[self.direction]['stop_base']
        desired_stop = stop_base + (-idx if self.direction in ['N', 'W'] else idx) * (self.size + spacing)
        ahead = None
        for v in others:
            if v == self: break
            ahead = v

        stop = False
        if not self.passed_center:
            if not is_green:
                if self.direction == 'N' and self.y + self.size >= stop_base: stop = True
                if self.direction == 'S' and self.y - self.size <= stop_base: stop = True
                if self.direction == 'E' and self.x - self.size <= stop_base: stop = True
                if self.direction == 'W' and self.x + self.size >= stop_base: stop = True

            if ahead:
                if self.direction in ['N', 'S'] and abs(ahead.y - self.y) < self.size + spacing: stop = True
                if self.direction in ['E', 'W'] and abs(ahead.x - self.x) < self.size + spacing: stop = True

        if stop and not self.passed_center:
            return

        self.x += self.dx * self.speed / BASE_SPEED
        self.y += self.dy * self.speed / BASE_SPEED
        if not self.passed_center and abs(self.x) < 0.05 and abs(self.y) < 0.05:
            self.passed_center = True
            self.state = 'depart'

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, 0)
        if self.direction == 'N': glRotatef(180, 0, 0, 1)
        elif self.direction == 'E': glRotatef(270, 0, 0, 1)
        elif self.direction == 'W': glRotatef(90, 0, 0, 1)
        glColor3f(1, 1, 1)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        width = self.size
        height = self.size / self.aspect_ratio
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(-width/2, -height/2)
        glTexCoord2f(1, 1); glVertex2f(width/2, -height/2)
        glTexCoord2f(1, 0); glVertex2f(width/2, height/2)
        glTexCoord2f(0, 0); glVertex2f(-width/2, height/2)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

def draw_road():
    glColor3f(0.1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex2f(-0.18, -1.0); glVertex2f(0.18, -1.0); glVertex2f(0.18, 1.0); glVertex2f(-0.18, 1.0)
    glVertex2f(-1.0, -0.18); glVertex2f(1.0, -0.18); glVertex2f(1.0, 0.18); glVertex2f(-1.0, 0.18)
    glEnd()
    glColor3f(1, 1, 1)
    glLineWidth(2)
    glBegin(GL_LINES)
    glVertex2f(0, -1); glVertex2f(0, 1)
    glVertex2f(-1, 0); glVertex2f(1, 0)
    glEnd()

def draw_signal(x, y, is_active, direction):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glColor3f(1, 0, 0) if not is_active else glColor3f(1, 1, 1)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(0, 0)
    for angle in range(0, 361, 10):
        rad = math.radians(angle)
        glVertex2f(0.02 * math.cos(rad), 0.02 * math.sin(rad))
    glEnd()

    glTranslatef(0, -0.05, 0)
    glColor3f(0, 1, 0) if is_active else glColor3f(1, 1, 1)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(0, 0)
    for angle in range(0, 361, 10):
        rad = math.radians(angle)
        glVertex2f(0.02 * math.cos(rad), 0.02 * math.sin(rad))
    glEnd()
    glPopMatrix()

def draw_signals():
    for idx, d in enumerate(DIRECTIONS):
        draw_signal(*SIGNAL_POSITIONS[d], idx == signal_index, d)

def spawn_vehicle():
    dir_choice = random.choice(DIRECTIONS)
    queue = vehicles[dir_choice]
    if not queue or abs(queue[-1].x if dir_choice in ['E', 'W'] else queue[-1].y) > 0.3:
        vehicles[dir_choice].append(Vehicle(dir_choice))

def main():
    global signal_index, signal_timer, spawn_timer
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    glClearColor(0.05, 0.05, 0.1, 1)
    gluOrtho2D(-1, 1, -1, 1)
    clock = pygame.time.Clock()

    for file in ["car-truck1.png", "car-truck2.png", "car-truck4.png", "car-truck5.png"]:
        tex_id, aspect = load_texture_with_aspect(file)
        car_textures.append(tex_id)
        car_aspect_ratios.append(aspect)

    running = True
    while running:
        glClear(GL_COLOR_BUFFER_BIT)
        draw_road()
        draw_signals()

        current = time.time()
        if current - signal_timer > SIGNAL_INTERVAL:
            signal_index = (signal_index + 1) % 4
            signal_timer = current

        if current - spawn_timer > 2:
            spawn_vehicle()
            spawn_timer = current

        for idx, d in enumerate(DIRECTIONS):
            green = (idx == signal_index)
            for v in vehicles[d]:
                v.update(green, vehicles[d])
                v.draw()
            vehicles[d] = [v for v in vehicles[d] if -1.5 < v.x < 1.5 and -1.5 < v.y < 1.5]

        pygame.display.flip()
        clock.tick(60)

        for e in pygame.event.get():
            if e.type == QUIT:
                running = False

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
