import logging
import operator
from bson import BSON
import bson.json_util
import bz2
import numpy
import io
import scipy
from gcviewer.image_manager import ArrayStackImageManager, PyGameArrayStackManager
from gcviewer.lookup_table import ArrayLookupTable
from gcviewer.scene import ImageStackScene
import png

logger = logging.getLogger(__name__)


class SimpleArrayStack():
    @classmethod
    def scene_from_data(cls, data):
        data_dict = BSON.decode(data)
        lut = ArrayLookupTable(cls._decode_array(data_dict['lookup_table']))
        print(set(bytes_to_array(data_dict['lookup_table']).flatten()))
        print(sorted(map(float, data_dict['frames'].keys())))
        frames = [numpy.flipud(numpy.rot90(cls._decode_array(value))) for key, value in
                  sorted(data_dict['frames'].items(), key=lambda x: int(x[0]))]
        # print(frames)
        image_manager = ArrayStackImageManager(frames)
        scene = ImageStackScene(image_manager, lut)
        return scene

    @classmethod
    def data_from_scene(cls, scene):
        lut_array = scene.lookup_table.array
        lut_array_values = set(lut_array.flatten())

        def frame_iterator():
            for frame_index in sorted(scene.image_manager.keys):
                frame = scene.image_manager.load_array(frame_index)
                yield frame

        stream = io.BytesIO()

        data = {'lookup_table': cls._encode_array(lut_array),
                'frames': {str(key): cls._encode_array(array) for key, array in enumerate(frame_iterator())}
        }

        stream.write(BSON.encode(data))
        stream.seek(0)
        return stream.getvalue()

    @classmethod
    def _encode_array(cls, array):
        return array_to_bytes(array)

    @classmethod
    def _decode_array(cls, data):
        array = bytes_to_array(data)
        array.flags.writeable = False
        return array


class SimpleImageStack(SimpleArrayStack):
    @classmethod
    def _encode_array(cls, array):
        stream = io.BytesIO()
        scipy.misc.imsave(stream, array, format='png')

    @classmethod
    def _decode_array(cls, data):
        scipy.misc.imread(data)

decoders = {'simple_array_stack': SimpleArrayStack}


def array_to_bytes(array):
    stream = io.BytesIO()
    numpy.save(stream, array)
    return stream.getvalue()


def bytes_to_array(string):
    stream = io.BytesIO(string)
    array = numpy.load(stream)
    return array


def read_file(file):
    wrapper = BSON.decode(bson.json_util.loads(file.read()))

    logger.debug('Loading gc file with content type,', wrapper['type'])
    decoder = decoders[wrapper['type']]
    logger.debug('Found decoder:', decoder)
    body = wrapper['data']
    if wrapper['compression'] == 'bz2':
        body = bz2.decompress(body)
    scene = decoder.scene_from_data(body)
    return scene


def write_file(file, scene):
    wrapper = {'encoder': 'gcviewer',
               'version': '0.1',
               'compression': 'bz2',
               'type': 'simple_array_stack',
               'data': bz2.compress(SimpleArrayStack.data_from_scene(scene))
    }
    file.write(bson.json_util.dumps(BSON.encode(wrapper)))



