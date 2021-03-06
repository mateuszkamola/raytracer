from cffi import FFI
from PIL import Image

ffi = FFI()
ffi.cdef("""
    typedef struct {
        double x, y, z;
    } point_t;

    typedef struct {
        double x, y, z;
    } vector_t;

    typedef struct {
        float red, green, blue;
    } color_t;

    typedef void* coloration;
    coloration coloration_color_new(float red, float green, float blue);
    coloration coloration_texture_new(char *path);
    void coloration_free(coloration);

    typedef void* surfacetype;
    surfacetype surfacetype_diffuse_new();
    surfacetype surfacetype_reflective_new(float reflectivity);
    surfacetype surfacetype_refractive_new(float index, float transparency);
    void surfacetype_free(surfacetype);

    typedef struct {
        coloration coloration;
        surfacetype surface;
        float albedo;
    } material_t;

    typedef struct {
        uint32_t x, y, width, height;
    } block_t;

    typedef void* scene;
    scene scene_new(uint32_t width, uint32_t height,
        double fov, double shadow_bias, uint32_t max_recursion_depth);
    scene scene_from_json(char *buffer);
    void scene_add_sphere(scene, const point_t *center, double radius,
        const material_t *material);
    void scene_add_plane(scene, const point_t *origin, const vector_t *normal,
        const material_t *material);
    void scene_add_spherical_light(scene, const point_t *position,
        const color_t *color, float intensity);
    void scene_add_directional_light(scene, const vector_t *direction,
        const color_t *color, float intensity);
    void scene_render(scene, const block_t *block, char *buffer, size_t length);
    char *scene_get_json(scene);
    void scene_free(scene);
    void string_free(char *string);
""")

C = ffi.dlopen("./../raytracer/ffi/target/release/raytracer_ffi.dll")

def point(x, y, z):
    point = ffi.new("point_t *")
    point.x = x
    point.y = y
    point.z = z
    return point

def vector(x, y, z):
    vector = ffi.new("vector_t *")
    vector.x = x
    vector.y = y
    vector.z = z
    return vector

def color(red, green, blue):
    color = ffi.new("color_t *")
    color.red = red
    color.green = green
    color.blue = blue
    return color

def material(coloration, surface, albedo):
    material = ffi.new("material_t *")
    material.coloration = coloration.get_raw()
    material.surface = surface.get_raw()
    material.albedo = albedo
    return material

def block(x, y, width, height):
    block = ffi.new("block_t *")
    block.x = x
    block.y = y
    block.width = width
    block.height = height
    return block

class Scene(object):
    def __init__(self, width, height, obj):
        self.__x = 0
        self.__y = 0
        self.__width = width
        self.__height = height
        self.__obj = obj

    @property
    def width(self):
        return self.__width

    @property
    def height(self):
        return self.__height

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        C.scene_free(self.__obj)
        self.__obj = None

    def add_sphere(self, center, radius, material):
        C.scene_add_sphere(self.__obj, center, radius, material)

    def add_plane(self, origin, normal, material):
        C.scene_add_plane(self.__obj, origin, normal, material)

    def add_spherical_light(self, position, color, intensity):
        C.scene_add_spherical_light(self.__obj, position, color, intensity)

    def add_directional_light(self, direction, color, intensity):
        C.scene_add_directional_light(self.__obj, direction, color, intensity)

    def set_viewport(self, x, y, width, height):
        self.__x = x
        self.__y = y
        self.__width = width
        self.__height = height

    def render_image(self):
        pixel_format = "RGBA" #The raytracer only supports one format
        return Image.frombuffer(pixel_format, (self.__width, self.__height),
            self.render_bytes(), "raw", pixel_format, 0, 1)

    def render_bytes(self):
        bytes_per_pixel = 4
        buffer_len = self.__width * self.__height * bytes_per_pixel
        buffer = ffi.new("char[]", buffer_len)
        view_block = block(self.__x, self.__y, self.__width, self.__height)
        C.scene_render(self.__obj, view_block, buffer, buffer_len)
        return ffi.buffer(buffer)

    def get_json(self):
        json_raw = C.scene_get_json(self.__obj)
        try:
            json_str = ffi.string(json_raw)
            return json_str
        finally:
            C.string_free(json_raw)

    @staticmethod
    def from_json(json):
        c_json = ffi.new("char[]", json)
        obj = C.scene_from_json(c_json)
        return Scene(None, None, obj)

    @staticmethod
    def create(width, height, fov, shadow_bias, max_recursion_depth):
        obj = C.scene_new(width, height, fov, shadow_bias, max_recursion_depth)
        return Scene(width, height, obj)

class Coloration(object):
    @staticmethod
    def color(red, green, blue):
        coloration = C.coloration_color_new(red, green, blue)
        return Coloration(coloration)

    @staticmethod
    def texture(path):
        c_path = ffi.new("char[]", str(path).encode())
        coloration = C.coloration_texture_new(c_path)
        return Coloration(coloration)

    def __init__(self, obj):
        self.__obj = obj;

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        C.coloration_free(self.__obj)
        self.__obj = None

    def get_raw(self):
        return self.__obj

class SurfaceType(object):
    @staticmethod
    def diffuse():
        surfacetype = C.surfacetype_diffuse_new();
        return SurfaceType(surfacetype)

    @staticmethod
    def reflective(reflectivity):
        surfacetype = C.surfacetype_reflective_new(reflectivity);
        return SurfaceType(surfacetype)

    @staticmethod
    def refractive(index, transparency):
        surfacetype = C.surfacetype_refractive_new(index, transparency);
        return SurfaceType(surfacetype)

    def __init__(self, obj):
        self.__obj = obj;

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        C.surfacetype_free(self.__obj)
        self.__obj = None

    def get_raw(self):
        return self.__obj
