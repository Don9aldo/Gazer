from __future__ import division, print_function, unicode_literals

from collections import Counter
import json
import os
from functools import wraps
import logging
from scipy import misc
import numpy as np

from lpt.lfp.tnt import Tnt

from gazer.modules.temp_folder_manager import TempFolderManager
from gazer.modules.dof.dof_data import DOFData
from gazer.modules.dof.scenes import ImageStackScene


def tnt_command_sequence(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        tnt = Tnt(verbose=True)
        result = f(tnt, *args, **kwargs)
        tnt.execute()
        return result

    return wrapper


@tnt_command_sequence
def make_depth_map(tnt, lfp_in, depth_out_folder, depth_out_file_fame):
    file_type = 'bmp'
    out_file = '{}.{}'.format(depth_out_file_fame, file_type)
    out_path = os.path.join(depth_out_folder, out_file)

    tnt.lfp_in(lfp_in)
    tnt.depthrep(file_type)
    tnt.depth_out(out_path)
    tnt.dir_out(depth_out_folder)


def read_depth_data(depth_dir, name):
    depth_map_path = os.path.join(depth_dir, '{}.bmp'.format(name))
    depth_meta_data_path = os.path.join(depth_dir, '{}.jsn'.format(name))
    depth_map = misc.imread(depth_map_path)
    # TODO: Reduce depth map to one value per pixel
    # depth_map = depth_map[..., ..., 0]
    with open(depth_meta_data_path) as meta_data_file:
        depth_meta = json.load(meta_data_file)
    return depth_map, depth_meta


def get_depth_data(lfp_in):
    with TempFolderManager() as tmp_dir:
        depth_out_file_fame = 'depth'
        make_depth_map(lfp_in, tmp_dir, depth_out_file_fame)
        return read_depth_data(tmp_dir, depth_out_file_fame)


@tnt_command_sequence
def make_focus_image(tnt, lfp_in, image_out, focus, calibration,
                     image_size=None):
    tnt.calibration_in(calibration)
    tnt.lfp_in(lfp_in)
    tnt.image_out(image_out)
    tnt.focus(str(focus))
    if image_size:
        tnt.width(image_size[0])
        tnt.height(image_size[1])


def get_main_depth_planes(depth_map, threshold=0.02):
    overall_count = depth_map.size
    counts = Counter(depth_map.flat)
    main_depth_planes = []
    for depth, depth_count in counts.iteritems():
        if depth_count > threshold * overall_count:
            main_depth_planes.append(depth)
    return main_depth_planes


def remap(value, from_range, to_range):
    from_start, from_end = from_range
    assert np.all(from_start <= value <= from_end), \
        "Value {} not between {}, {}".format(value, from_start, from_end)
    from_range_len = from_end - from_start
    normalized_value = (value - from_start) / from_range_len
    to_start, to_end = to_range
    assert to_start < to_end
    to_range_len = to_end - to_start
    remapped_value = (normalized_value * to_range_len) + to_start
    return remapped_value


def value_map_to_index_map(value_map, index_list):
    """
    Return every value in the value_map with the index of
    the closest value from the index_list.

    Parameters
    ----------
    value_map : ndarray
    index_list : list
    """
    index_array = np.array(index_list)

    def indexify(val):
        dist = index_array - val
        abs_dist = np.abs(dist)
        return abs_dist.argmin()

    result = [indexify(x) for x in value_map.flat]
    result = np.array(result).reshape(value_map.shape)
    return result


def lambda_from_depth(value, depth_meta):
    """
    Return lambda value for raw value from depth map.

    Parameters
    ----------
    value: numeric
        Value from the depth map generated by the Lytro api.
    depth_meta: dict
        Dictionary containing the metadata provided by the Lytro api.

    Returns
    -------
    Lambda value for raw depth map value.

    """

    # The values from the depth map need be considered as normalised values
    # in the range 0...255
    # And will be linearly transformed to the lambda range
    # indicated by the metadata
    depth_range = 0, 255
    lambda_range = depth_meta['LambdaMin'], depth_meta['LambdaMax']
    lambda_value = remap(value, depth_range, lambda_range)
    return lambda_value


def ifp_to_dof_data(lfp_in, calibration, out_path, status_callback=None):
    depth_map, depth_meta = get_depth_data(lfp_in)

    frame_mapping = {}
    file_basename = os.path.basename(str(lfp_in)).split('.')[0]
    file_name_template = file_basename + '_f_{}.jpg'
    unique_depth_values = np.unique(depth_map)
    for num, depth in enumerate(unique_depth_values):
        lambda_value = lambda_from_depth(depth, depth_meta)
        out_image = os.path.join(out_path,
                                 file_name_template.format(lambda_value))

        debug_msg = "Processing image {} - {}/{}"
        logging.debug(debug_msg.format(out_image,
                                       num + 1,
                                       len(unique_depth_values)))
        if status_callback:
            status_callback('{}/{}'.format(num + 1, len(unique_depth_values)))
        if not os.path.exists(out_image):
            make_focus_image(lfp_in, out_image, lambda_value, calibration)
        if depth not in frame_mapping:
            image = misc.imread(out_image)
            frame_mapping[depth] = image

    return DOFData(depth_map, frame_mapping)


def read_ifp(file_name, config, status_callback=None):
    logging.debug('Loading IFP or IFR file: ' + file_name)

    calibration = config['calibration_path']
    scene = None

    with TempFolderManager() as tmp_dir:
        try:
            dof_data = ifp_to_dof_data(file_name,
                                       calibration,
                                       tmp_dir,
                                       status_callback)
            scene = ImageStackScene.from_dof_data(dof_data)

        except RuntimeError:
            logging.exception("Error loading ifp file " + file_name)

    logging.debug('Finished Loading.')

    return scene
