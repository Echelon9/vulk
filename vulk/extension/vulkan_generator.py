from contextlib import contextmanager
import requests
import xmltodict


VULKAN_PLATEFORM_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
                        'Vulkan-Docs/1.0/src/vulkan/vk_platform.h')
VULKAN_H_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
                'Vulkan-Docs/1.0/src/vulkan/vulkan.h')
VK_XML_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
              'Vulkan-Docs/1.0/src/spec/vk.xml')
OUT_FILE = 'vulkanmodule.c'

DEFINE_HEADER = '''
#include <Python.h>
#include <dlfcn.h>

#define VK_NO_PROTOTYPES

#if defined(ANDROID) || defined (__ANDROID__)
  #define VK_USE_PLATFORM_ANDROID_KHR 1
#elif defined(_WIN32)
  #define VK_USE_PLATFORM_WIN32_KHR 1
#elif defined(__linux__)
  #define VK_USE_PLATFORM_XLIB_KHR 1
#endif

#ifdef __unix__

#define LOAD_SDK() dlopen("libvulkan.so", RTLD_NOW);

#elif defined(_WIN32) || defined(WIN32)

#define LOAD_SDK() LoadLibrary("vulkan-1.dll");
#define dlsym GetProcAddress

#endif
'''

# Struct which need to be surrounded by #define
MAPPING_EXTENSION_DEFINE = {
    'VkAndroidSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_ANDROID_KHR',
    'VkMirSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_MIR_KHR',
    'VkWaylandSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_WAYLAND_KHR',
    'VkWin32SurfaceCreateInfoKHR': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkImportMemoryWin32HandleInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkExportMemoryWin32HandleInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkWin32KeyedMutexAcquireReleaseInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkXcbSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_XCB_KHR',
    'VkXlibSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_XLIB_KHR',
    'VkRect3D': 'hackdefine'  # VkRect3D is not used
}


vulkan_plateform = None
vulkan_h = None
vk_xml = None
vk_extension_functions = None
vk_all_functions = None
return_structs = None
create_structs = None
structs = None
handles = None
out = None


def main():
    global vulkan_plateform
    global vulkan_h
    global vk_xml
    global vk_extension_functions
    global vk_all_functions
    global return_structs
    global create_structs
    global out
    global structs
    global handles

    vulkan_plateform = requests.get(VULKAN_PLATEFORM_URL).text
    vulkan_h = clean_vulkan_h(requests.get(VULKAN_H_URL).text)
    vk_xml = xmltodict.parse(requests.get(VK_XML_URL).text)
    vk_extension_functions = get_vk_extension_functions()
    vk_all_functions = get_all_vk_functions()
    structs = get_structs()
    return_structs = get_structs_returned_only()
    create_structs = get_create_structs()
    handles = get_handles()

    out = open(OUT_FILE, 'w')

    add_header()
    add_vk_plateform()
    add_vk_h()
    add_vulkan_function_prototypes()
    add_initsdk()
    add_pyhandles()
    add_pyobject()
    add_pymethod()
    add_pymodule()
    add_pyinit()

    out.close()


def clean_vulkan_h(vulkan_h):
    cleaned = ""
    for line in vulkan_h.splitlines(True):
        if '#include "vk_platform.h"' in line:
            continue
        line = line.replace(' const ', ' ')
        line = line.replace('const* ', '*')
        cleaned += line

    return cleaned


def get_vk_extension_functions():
    names = set()
    for extension in vk_xml['registry']['extensions']['extension']:
        if 'command' not in extension['require']:
            continue
        if type(extension['require']['command']) is not list:
            extension['require']['command'] = [
                extension['require']['command']]

        for command in extension['require']['command']:
            names.add(command['@name'])

    return names


def get_all_vk_functions():
    return set([c['proto']['name']
               for c in vk_xml['registry']['commands']['command']])


def get_structs():
    """Return structs

    Keep informations of xmltodict
    """
    return [s for s in vk_xml['registry']['types']['type']
            if s.get('@category', None) == 'struct']


def get_handles():
    """Return set of name handles """
    return set([s['name'] for s in vk_xml['registry']['types']['type']
               if s.get('@category', None) == 'handle'])


def get_structs_returned_only():
    return set([s['@name'] for s in structs
               if '@returnedonly' in s and s['@returnedonly'] == 'true'])


def get_create_structs():
    return set([s['@name'] for s in structs if 'Create' in s['@name']])


def add_header():
    header = DEFINE_HEADER
    header += '\n'
    out.write(header)


def add_vk_plateform():
    out.write("// BEGIN VULKAN PLATEFORM\n")
    out.write(vulkan_plateform)
    out.write("// END VULKAN PLATEFORM\n")


def add_vk_h():
    out.write("// BEGIN VULKAN H\n")
    out.write(vulkan_h)
    out.write("// END VULKAN H\n")


def add_pyinit():
    out.write("\n\nPyMODINIT_FUNC PyInit_vulkan(void) {\n")
    create_module()
    add_constants()
    add_object_in_init()
    out.write("return module;\n}\n")


def add_pyhandles():
    for handle in handles:
        out.write("""
            static PyObject* PyHandle_{0} (PyObject *self, PyObject *args) {{
                  {0}* handle = malloc(sizeof({0}));
                  PyObject* value = PyCapsule_New(handle, "{0}", NULL);
                  if (value == NULL) return NULL;
                  return value;
            }}
            """.format(handle))


def add_object_in_init():
    for struct in structs:
        with check_struct_extension(struct):
            out.write('''
                if (PyType_Ready(&Py{0}Type) < 0)
                    return NULL;
                Py_INCREF(&Py{0}Type);
                PyModule_AddObject(module, "{0}", (PyObject *)&Py{0}Type);
            '''.format(struct['@name']))


def get_member_type_name(member):
    name = member['type']
    if '#text' in member:
        name += ' ' + member['#text']
    return name


def get_signatures():
    names = set()
    for s in structs:
        for m in s['member']:
            name = m['type']
            if '#text' in m:
                name += ' ' + m['#text']
            names.add(name)
    return names


def pyobject_to_val(member):
    constchar_convert = '''
        PyObject * ascii_str = PyUnicode_AsASCIIString(value);
        char* tmp = PyBytes_AsString(ascii_str);
        (self->base)->{1} = strdup(tmp);
        Py_DECREF(ascii_str);
        '''
    arraychar_convert = '''
        PyObject * ascii_str = PyUnicode_AsASCIIString(value);
        char* tmp = PyBytes_AsString(ascii_str);
        strcpy((self->base)->{1}, tmp);
        Py_DECREF(ascii_str);
        '''

    listchar_convert = '''
        int nb = PyList_Size(value);
        char** tmp = malloc(sizeof(char*)*nb + 1);
        int i;
        for (i = 0; i < nb; i++) {{
            PyObject* ascii_str = PyUnicode_AsASCIIString(
            PyList_GetItem(value, i));
            char* tmp2 = PyBytes_AsString(ascii_str);
            tmp[i] = strdup(tmp2);
            Py_DECREF(ascii_str);
        }}
        tmp[i] = NULL; // sentinel
        (self->base)->{1} = tmp;
        '''

    listfloat_convert = '''
        int nb = PyList_Size(value);
        int i;
        for (i = 0; i < nb; i++) {{
            float tmp = (float) PyFloat_AsDouble(PyList_GetItem(value, i));
            ((self->base)->{1})[i] = tmp;
        }}
        '''

    pointerfloat_convert = '''
        float tmp = (float) PyFloat_AsDouble(value);
        float *t = malloc(sizeof(float));
        memcpy(t, &tmp, sizeof(float));
        (self->base)->{1} = t;
        '''

    listuint32_convert = (
        listfloat_convert
        .replace('float', 'uint32_t')
        .replace('PyFloat_AsDouble', 'PyLong_AsLong'))

    listuint8_convert = listuint32_convert.replace('uint32_t', 'uint8_t')

    pointeruint32_convert = (
        pointerfloat_convert
        .replace('float', 'uint32_t')
        .replace('PyFloat_AsDouble', 'PyLong_AsLong'))

    mapping = {
        'uint32_t':
        '(self->base)->{1} = (uint32_t) PyLong_AsLong(value);',
        'float':
        '(self->base)->{1} = (float) PyFloat_AsDouble(value);',
        'int32_t':
        '(self->base)->{1} = (int32_t) PyLong_AsLong(value);',
        'char []': arraychar_convert,
        'char const *': constchar_convert,
        'char const * const*': listchar_convert,
        'float [2]': listfloat_convert,
        'float [4]': listfloat_convert,
        'float const *': pointerfloat_convert,
        'size_t':
        '(self->base)->{1} = (size_t) PyLong_AsLong(value);',
        'uint32_t [2]': listuint32_convert,
        'uint32_t [3]': listuint32_convert,
        'uint32_t const *': pointeruint32_convert,
        'uint64_t':
        '(self->base)->{1} = (uint64_t) PyLong_AsLong(value);',
        'uint8_t []': listuint8_convert,
        'void const *': '(self->base)->{1} = NULL;',
        'void *': '(self->base)->{1} = NULL;',
        'Window':
        '(self->base)->{1} = (XID) PyLong_AsLong(value);',
        'Display *':
        '(self->base)->{1} = (Display *) PyLong_AsLong(value);'
    }

    signatures = [s for s in get_signatures() if s.startswith('VK')]

    for signature in signatures:
        vkname = signature.split()[0]

        # pointer
        if signature.endswith('*'):
            pass
            mapping[signature] = '''
                '(->base)->{1} = (value->base)
            '''
        # array
        elif signature.endswith(']'):
            pass
        # base
        else:
            mapping[signature] = '''
                '(->base)->{1} = *(value->base)
            '''

    name = get_member_type_name(member)
    return mapping.get(name, None)


def val_to_pyobject(member):
    listchar_convert = '''
        if ({0}[0] == NULL) return PyList_New(0);;
        PyObject* value = PyList_New(0);
        int i = 0;
        while ({0}[i] != NULL) {{{{
            PyObject* py_tmp = PyUnicode_FromString((const char *) {0}[i]);
            PyList_Append(value, py_tmp);
            i++;
        }}}}
        '''

    listfloat_convert = '''
        PyObject* value = PyList_New(0);
        int nb = sizeof({0}) / sizeof({0}[0]);
        int i = 0;
        for (i = 0; i < nb; i++) {{{{
            PyObject* py_tmp = PyFloat_FromDouble((double) {0}[i]);
            PyList_Append(value, py_tmp);
        }}}}
        '''

    listuint32_convert = (
        listfloat_convert
        .replace('double', 'long')
        .replace('PyFloat_FromDouble', 'PyLong_FromLong'))

    listuint8_convert = listuint32_convert

    mapping = {
        'uint32_t':
        'PyObject* value = PyLong_FromLong((long) {});',
        'float':
        'PyObject* value = PyFloat_FromDouble((double) {});',
        'int32_t':
        'PyObject* value = PyLong_FromLong((long) {});',
        'char []':
        'PyObject* value = PyUnicode_FromString((const char *) {});',
        'char const *':
        'PyObject* value = PyUnicode_FromString((const char *) {});',
        'char const * const*': listchar_convert,
        'float [2]': listfloat_convert,
        'float [4]': listfloat_convert,
        'float const *':
        'PyObject* value = PyFloat_FromDouble((double) (*({})));',
        'size_t':
        'PyObject* value = PyLong_FromLong((long) {});',
        'uint32_t [2]': listuint32_convert,
        'uint32_t [3]': listuint32_convert,
        'uint32_t const *':
        'PyObject* value = PyLong_FromLong((long) (*({})));',
        'uint64_t':
        'PyObject* value = PyLong_FromLong((long) {});',
        'uint8_t []': listuint8_convert,
        'void const *': 'Py_INCREF(Py_None);PyObject* value = Py_None;',
        'void *': 'Py_INCREF(Py_None);PyObject* value = Py_None;',
        'Window':
        'PyObject* value = PyLong_FromLong((long) {});',
        'Display *': 'Py_INCREF(Py_None);PyObject* value = Py_None;',
    }

    signatures = [s for s in get_signatures() if s.startswith('VK')]

    for signature in signatures:
        vkname = signature.split()[0]

        # pointer
        if signature.endswith('*'):
            pass
            mapping[signature] = '''
                PyObject* value = PyObject_CallObject(
                    (PyObject *) &Py{}, NULL);
                value->base = {{}}->base;
            '''.format(vkname)
        # array
        elif signature.endswith(']'):
            pass
        # base
        else:
            mapping[signature] = '''
                PyObject* value = PyObject_CallObject(
                    (PyObject *) &Py{}, NULL);
                value->base = {{}}->base;
            '''.format(vkname)

    name = get_member_type_name(member)
    value = mapping.get(name, None)
    if value:
        return value.format('(self->base)->{1}')
    return None


def add_pyobject():
    def add_struct(s):
        definition = '''
            typedef struct {{ PyObject_HEAD {0} *base; }}
            Py{0};
            '''
        out.write(definition.format(s['@name']))

    def add_del(s):
        definition = '''
            static void Py{0}_del(Py{0}* self) {{
                Py_TYPE(self)->tp_free((PyObject*)self); }}
            '''
        out.write(definition.format(s['@name']))

    def add_new(s):
        definition = '''
            static PyObject *
            Py{0}_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
            {{
                Py{0} *self;
                self = (Py{0} *)type->tp_alloc(type, 0);
                if ( self != NULL) {{
                    self->base = malloc(sizeof({0}));
                    if (self->base == NULL) {{
                        PyErr_SetString(PyExc_MemoryError,
                            "Cannot allocate memory for {0}");
                        return NULL;
                    }}
                }}

                return (PyObject *)self;
            }}
            '''
        out.write(definition.format(s['@name']))

    def add_init(s):
        definition = '''
            static int
            Py{0}_init(Py{0} *self, PyObject *args, PyObject *kwds) {{
            '''.format(s['@name'])

        if s['@name'] not in return_structs:
            definition += add_init_vars(s['member'])
            definition += add_init_kwlist(s['member'])
            definition += add_init_parse(s['member'])

        definition += 'return 0; }'

        out.write(definition)

    def add_init_vars(members):
        result = []
        for member in members:
            result.append('PyObject* %s = NULL;' % member['name'])
        return '\n'.join(result)

    def add_init_kwlist(members):
        result = 'static char *kwlist[] = {'
        for member in members:
            result += '"{}",'.format(member['name'])
        result += 'NULL};'
        return result

    def add_init_parse(members):
        result = 'PyArg_ParseTupleAndKeywords(args, kwds, "'
        result += 'O' * len(members)
        result += '", kwlist'
        for member in members:
            result += ', &{}'.format(member['name'])
        result += ')'
        return 'if(!%s) return -1;' % result

    def add_setters(s):
        def add_setter(member):
            definition = '''
            static int Py{0}_set{1}(Py{0} *self, PyObject *value,
                                    void *closure) {{
                if (value == NULL) {{
                    PyErr_SetString(PyExc_TypeError, "Error with {1}");
                    return -1;
                }}
            '''

            convert = pyobject_to_val(member)

            if convert:
                definition += convert
            else:
                return

            definition += '''
                return 0;
            }}
            '''
            out.write(definition.format(s['@name'], member['name']))

        def add_getter(member):
            definition = '''
            static PyObject * Py{0}_get{1}(Py{0} *self, void *closure){{
            '''

            convert = val_to_pyobject(member)
            if convert:
                definition += convert
            else:
                return

            definition += '''
                Py_INCREF(value);
                return value;
            }}
            '''
            out.write(definition.format(s['@name'], member['name']))

        def add_getter_setter(s):
            out.write('''
                static PyGetSetDef Py{}_getsetters[] = {{
                '''.format(s['@name']))

            for member in s['member']:
                if not val_to_pyobject(member):
                    continue
                sname = s['@name']
                mname = member['name']
                getter = '(getter)Py{0}_get{1}'.format(sname, mname)
                setter = '(setter)Py{0}_set{1}'.format(sname, mname)

                out.write('''
                    {{ "{}", {}, {}, "", NULL}},
                '''.format(mname, getter, setter))

            out.write('{NULL}};\n')

        for member in s['member']:
            add_setter(member)
            add_getter(member)
        add_getter_setter(s)

    def add_type(s):
        out.write('''
            static PyTypeObject Py{0}Type = {{
                PyVarObject_HEAD_INIT(NULL, 0)
                "vulkan.{0}", sizeof(Py{0}), 0,
                (destructor)Py{0}_del,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,Py_TPFLAGS_DEFAULT,
                "{0} object",0,0,0,0,0,0,0,0,
                Py{0}_getsetters,0,0,0,0,0,0,0,Py{0}_new,}};
        '''.format(s['@name']))

    for struct in structs:
        with check_struct_extension(struct):
            for fun in (add_struct, add_del, add_new, add_setters,
                        add_init, add_type):
                fun(struct)


@contextmanager
def check_struct_extension(struct):
    mapping = MAPPING_EXTENSION_DEFINE
    try:
        if struct['@name'] in mapping:
            out.write('\n#ifdef {}\n'
                      .format(mapping[struct['@name']]))
        yield
    finally:
        if struct['@name'] in mapping:
            out.write('\n#endif\n')


def add_pymodule():
    name = '"vulkan"'
    doc = '"Vulkan module"'
    out.write('''
        static struct PyModuleDef vulkanmodule = {{
            PyModuleDef_HEAD_INIT, {}, {}, -1, VulkanMethods}};
        '''.format(name, doc))


def create_module():
    out.write('''
        PyObject* module;
        module = PyModule_Create(&vulkanmodule);
        if (module == NULL) return NULL;
    ''')


def add_vulkan_function_prototypes():
    result = []

    for command in vk_all_functions - vk_extension_functions:
        name = command
        name_pfn = 'PFN_{}'.format(name)
        result.append('static {} {};'.format(name_pfn, name))

    out.write('\n')
    out.write('\n'.join(result))
    out.write('\n')


def add_constants():
    result = []

    def add_result(name, value):
        result.append('PyModule_AddIntConstant(module, "{}", {})'.format(
            name, value))

    # List enums
    for enum in vk_xml['registry']['enums']:
        name = ""
        value = ""

        # List constant in enum
        if type(enum['enum']) is not list:
            enum['enum'] = [enum['enum']]

        for constant in enum['enum']:
            if '@bitpos' in constant:
                value = str(int(constant['@bitpos']) + 1).zfill(8)
                constant['@value'] = '0x{}'.format(value)
            name = constant["@name"]
            value = constant["@value"]
            add_result(name, value)

    text = '\n\n'
    text += ';\n'.join(result)
    text += ';\n'
    out.write(text)


def add_initsdk():
    functions = []
    for command in vk_all_functions - vk_extension_functions:
        name = command
        name_pfn = 'PFN_{}'.format(name)
        functions.append('''
                         {0} = ({1})dlsym(vk_sdk, "{0}");
                         if( {0} == NULL ) {{
                             PyErr_SetString(PyExc_ImportError,
                                             "Can't load {0} in sdk");
                             return NULL;
                         }}
                         '''
                         .format(name, name_pfn))

    out.write('''
        static PyObject * load_sdk(PyObject *self, PyObject *args) {
            void* vk_sdk = LOAD_SDK();
            if (vk_sdk == NULL) {
                PyErr_SetString(PyExc_ImportError,
                                "Can't find vulkan sdk");
                return NULL;
            }

            '''+'\n'.join(functions)+'''

            Py_INCREF(Py_None);
            return Py_None;
        }
    ''')


def add_pymethod():
    functions = []

    # Add load_sdk function
    functions.append({'name': 'load_sdk',
                      'value': 'load_sdk',
                      'arg': 'METH_NOARGS',
                      'doc': '"Load SDK"'})

    # Add handle functions
    for handle in handles:
        functions.append({'name': handle,
                          'value': 'PyHandle_' + handle,
                          'arg': 'METH_NOARGS',
                          'doc': '"Handle"'})

    out.write('\nstatic PyMethodDef VulkanMethods[] = {\n')

    for fun in functions:
        out.write('{{"{}", {}, {}, {}}},\n'.format(
            fun['name'], fun['value'], fun['arg'], fun['doc']))

    out.write('\n{NULL, NULL, 0, NULL} };\n')


if __name__ == '__main__':
    main()
