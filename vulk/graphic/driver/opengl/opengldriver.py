import ctypes

import OpenGL.GL as gl

from vulk.graphic.driver.opengl import meshdata, shaderprogram
from vulk.graphic.driver.opengl.constant import gl_constant


class OpenGLDriver():
    def __init__(self, config):
        self.mesh_data = meshdata.MeshData
        self.shader_program = shaderprogram.ShaderProgram
        self.clear = clear
        self.render = render


def clear(color=None, depth=None):
    bit = 0

    if color:
        gl.glClearColor(*color)
        bit |= gl.GL_COLOR_BUFFER_BIT

    if depth:
        gl.glClearDepth(depth)
        bit |= gl.GL_DEPTH_BUFFER_BIT

    gl.glClear(bit)


def render(primitive_type, offset, count):
    gl.glDrawElements(gl_constant(primitive_type), count,
                      gl.GL_UNSIGNED_SHORT, ctypes.c_void_p(offset * 2))
