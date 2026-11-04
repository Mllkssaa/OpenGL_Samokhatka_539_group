import sys
import random
import pygame
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader

#роздільна здатність вікна
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

VERTEX_SHADER = """
#version 330 core
layout (location = 0) in vec2 aPos;

uniform vec2 u_position;
uniform vec2 u_scale;

void main()
{
    vec2 pos = aPos * u_scale + u_position;
    gl_Position = vec4(pos, 0.0, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;

uniform vec3 u_color;

void main()
{
    FragColor = vec4(u_color, 1.0);
}
"""

class ArkanoidGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption("Arkanoid with Power-ups - OpenGL / Python")

        self.shader = compileProgram(
            compileShader(VERTEX_SHADER, GL_VERTEX_SHADER),
            compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER),
        )

        vertices = [
            0.0, 1.0,
            1.0, 0.0,
            0.0, 0.0,

            0.0, 1.0,
            1.0, 1.0,
            1.0, 0.0
        ]

        self.quad_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.quad_vbo)
        glBufferData(GL_ARRAY_BUFFER, sizeof(GLfloat) * len(vertices), (GLfloat * len(vertices))(*vertices), GL_STATIC_DRAW)

        self.quad_vao = glGenVertexArrays(1)
        glBindVertexArray(self.quad_vao)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(GLfloat), ctypes.c_void_p(0))

        #ракетка
        self.paddle_width = 0.3
        self.paddle_height = 0.04
        self.paddle_x = -self.paddle_width / 2
        self.paddle_y = -0.85
        self.paddle_speed = 0.02

        #м'яч
        self.ball_size = 0.04
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.ball_vx = 0.01
        self.ball_vy = -0.015

        #цеглини та бонуси
        self.bricks = []
        self.power_ups = [] #список активних падаючих бонусів
        self.init_bricks()

        self.clock = pygame.time.Clock()

    def init_bricks(self):
        self.bricks = []
        rows = 5
        cols = 8
        brick_width = 0.22
        brick_height = 0.06
        gap = 0.02
        start_x = -0.95
        start_y = 0.9

        colors = [
            (0.9, 0.2, 0.2),
            (0.9, 0.5, 0.1),
            (0.9, 0.9, 0.1),
            (0.2, 0.8, 0.2),
            (0.2, 0.6, 0.9)
        ]

        for r in range(rows):
            for c in range(cols):
                bx = start_x + c * (brick_width + gap)
                by = start_y + r * (brick_height + gap)
                self.bricks.append({
                    'x': bx, 'y': by, 'w': brick_width, 'h': brick_height,
                    'color': colors[r], 'active': True
                })

    def reset_ball(self):
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.ball_vx = 0.01
        self.ball_vy = -0.015

    def update(self):
        #керування ракеткою
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.paddle_x -= self.paddle_speed
            if self.paddle_x < -1.0: self.paddle_x = 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.paddle_x += self.paddle_speed
            if self.paddle_x + self.paddle_width > 1.0:
                self.paddle_x = 1.0 - self.paddle_width

        #рух мяча
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        #відбивання від стін
        if self.ball_x <= -1.0:
            self.ball_x = -1.0
            self.ball_vx = -self.ball_vx
        elif self.ball_x + self.ball_size >= 1.0:
            self.ball_x = 1.0 - self.ball_size
            self.ball_vx = -self.ball_vx

        if self.ball_y + self.ball_size >= 1.0:
            self.ball_y = 1.0 - self.ball_size
            self.ball_vy = -self.ball_vy

        if self.ball_y <= -1.0:
            self.reset_ball()
            self.power_ups.clear()

        #колізія з ракеткою
        if (self.ball_x < self.paddle_x + self.paddle_width and
            self.ball_x + self.paddle_size > self.paddle_x and
            self.ball_y < self.paddle_y + self.paddle_height and
            self.ball_y + self.ball_size > self.paddle_y):

            self.ball_y = self.paddle_y + self.paddle_height
            self.ball_vy = -self.ball_vy
            hit_offset = (self.ball_x + self.ball_size / 2) - (self.paddle_x + self.paddle_width / 2)
            self.ball_vx += hit_offset * 0.02

        #колізія з цнглинами
        for brick in self.bricks:
            if not brick['active']: continue

            if (self.ball_x < brick['x'] + brick['w'] and
                self.ball_x + self.ball_size > brick['x'] and
                self.ball_y < brick['y'] + brick['h'] and
                self.ball_y + self.ball_size > brick['y']):

                brick['active'] = False
                self.ball_vy = -self.ball_vy

                #шанс 35% випадіння бонусу
                if random.random() < 0.35:
                    p_type = random.choice(['expand', 'shrink', 'speed_up'])
                    p_color = (0.1, 0.9, 0.1) if p_type == 'expand' else ((0.9, 0.1, 0.1) if p_type == 'shrink' else (0.9, 0.6, 0.1))
                    self.power_ups.append({
                        'x': brick['x'] + brick['w'] / 2 - 0.03,
                        'y': brick['y'],
                        'w': 0.06, 'h': 0.04,
                        'type': p_type,
                        'color': p_color
                    })
                break

        #оновлення та рух падаючих бонусів
        for p in self.power_ups[:]:
            p['y'] -= 0.08 #швидкість падіння

            #перевірка збору бонуса ракеткою
            if (p['x'] < self.paddle_x + self.paddle_width and
                    p['x'] + p['w'] > self.paddle_x and
                    p['y'] < self.paddle_y + self.paddle_height and
                    p['y'] + p['h'] > self.paddle_y):

                    #застосування ефекту
                    if p['type'] == 'expand':
                        self.paddle_width = min(0.5, self.paddle_width + 0.1)
                    elif p['type'] == 'shrink':
                        self.paddle_width = max(0.15, self.paddle_width - 0.1)
                    elif p['type'] == 'speed_up':
                        self.ball_vx *= 1.3
                        self.ball_vy *= 1.3

                    self.power_ups.remove(p)
                elif p['y'] < -1.0:
                    self.power_ups.remove(p)

        def render(self):
            glClearColor(0.1, 0.1, 0.15, 1.0)
            glClear(GL_COLOR_BUFFER_BIT)

            glUseProgram(self.shader)
            glBindVertexArray(self.quad_vbo)

            #1. цеглини
            for brick in self.bricks:
                if brick['active']:
                    glUniform2f(glGetUniformLocation(self.shader, "u_position"), brick['x'], brick['y'])
                    glUniform2f(glGetUniformLocation(self.shader, "u_scale"), brick['w'], brick['h'])
                    glUniform3f(glGetUniformLocation(self.shader, "u_color"), *brick['color'])
                    glDrawArrays(GL_TRIANGLES, 0, 6)

            #2. бонуси які падають
            for p in self.power_ups:
                glUniform2f(glGetUniformLocation(self.shader, "u_position"), p['x'], p['y'])
                glUniform2f(glGetUniformLocation(self.shader, "u_scale"), p['w'], p['h'])
                glUniform3f(glGetUniformLocation(self.shader, "u_color"), *p['color'])
                glDrawArrays(GL_TRIANGLES, 0, 6)

            #3.ракетка
            glUniform2f(glGetUniformLocation(self.shader, "u_position"), self.paddle_x, self.paddle_y)
            glUniform2f(glGetUniformLocation(self.shader, "u_scale"), self.paddle_width, self.paddle_height)
            glUniform3f(glGetUniformLocation(self.shader, "u_color"), 0.2, 0.8, 1.0)
            glDrawArrays(GL_TRIANGLES, 0, 6)

            #4. мяч
            glUniform2f(glGetUniformLocation(self.shader, "u_position"), self.ball_x, self.ball_y)
            glUniform2f(glGetUniformLocation(self.shader, "u_scale"), self.ball_size, self.ball_size)
            glUniform3f(glGetUniformLocation(self.shader, "u_color"), 1.0, 0.8, 0.2)
            glDrawArrays(GL_TRIANGLES, 0, 6)

            pygame.display.flip()

        def run(self):
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                self.update()
                self.render()
                self.clock.tick(60)

            pygame.quit()
            sys.exit()

    if __name__ == '__main__':
        game = ArkanoidGame()
        game.run()