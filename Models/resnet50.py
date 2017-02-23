# -*- coding: utf-8 -*-
"""
Created on Thurs Feb 9 10:55:07 2017

@author: Dan Salo

ResNet-50 feature extractor from TF-Slim
"""

import sys
sys.path.append('../')

from Lib.TensorBase.tensorbase.base import Data

import tensorflow as tf

from tensorflow.contrib.slim.python.slim.nets import resnet_utils
from tensorflow.python.training import saver as tf_saver

from tensorflow.python import pywrap_tensorflow

slim = tf.contrib.slim
resnet_arg_scope = resnet_utils.resnet_arg_scope

flags = {
    'data_directory': '../Data/data_trans/',  # Location of training/testing files
    'save_directory': '../Logs/',  # Where to create model_directory folder
    'model_directory': 'conv5/',  # Where to create 'Model[n]' folder
    'batch_size': 1,
    'resnet_restore_file': "/home/kd/Documents/tf-Faster-RCNN/Models/resnet_v1_50.ckpt",
    'display_step': 20,  # How often to display loss
    'num_classes': 11,  # 10 digits, +1 for background
    'classes': ('__background__', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'),
    'anchor_scales': [1, 2, 3]
}


@slim.add_arg_scope
def bottleneck(inputs, depth, depth_bottleneck, stride, rate=1, outputs_collections=None, scope=None):
    with tf.variable_scope(scope, 'bottleneck_v1', [inputs]) as sc:
        depth_in = slim.utils.last_dimension(inputs.get_shape(), min_rank=4)
        if depth == depth_in:
            shortcut = resnet_utils.subsample(inputs, stride, 'shortcut')
        else:
            shortcut = slim.conv2d(inputs, depth, [1, 1], stride=stride, activation_fn=None, scope='shortcut')
        residual = slim.conv2d(inputs, depth_bottleneck, [1, 1], stride=1, scope='conv1')
        residual = resnet_utils.conv2d_same(residual, depth_bottleneck, 3, stride, rate=rate, scope='conv2')
        residual = slim.conv2d(residual, depth, [1, 1], stride=1, activation_fn=None, scope='conv3')
        output = tf.nn.relu(shortcut + residual)

    return slim.utils.collect_named_outputs(outputs_collections, sc.original_name_scope, output)


def resnet50(inputs, is_training=True, output_stride=None, include_root_block=True, reuse=None, scope=None):

    # These are the blocks for resnet 50
    blocks = [resnet_utils.Block(
            'block1', bottleneck, [(256, 64, 1)] * 2 + [(256, 64, 2)]),
        resnet_utils.Block(
            'block2', bottleneck, [(512, 128, 1)] * 3 + [(512, 128, 2)]),
        resnet_utils.Block(
            'block3', bottleneck, [(1024, 256, 1)] * 5 + [(1024, 256, 2)]),
        resnet_utils.Block(
            'block4', bottleneck, [(2048, 512, 1)] * 3)]

    # Initialize Model
    with tf.variable_scope(scope, 'resnet_v1_50', [inputs], reuse=reuse):
        with slim.arg_scope([slim.conv2d, bottleneck, resnet_utils.stack_blocks_dense]):
            with slim.arg_scope([slim.batch_norm], is_training=is_training) as scope:
                net = inputs
                if include_root_block:
                    if output_stride is not None:
                        if output_stride % 4 != 0:
                            raise ValueError('The output_stride needs to be a multiple of 4.')
                        output_stride /= 4
                    net = resnet_utils.conv2d_same(net, 64, 7, stride=2, scope='conv1')
                    net = slim.max_pool2d(net, [3, 3], stride=2, scope='pool1')
                net = resnet_utils.stack_blocks_dense(net, blocks, output_stride)
    return net


def read_and_decode(example_serialized):
    """ Read and decode binarized, raw MNIST dataset from .tfrecords file generated by clutterMNIST.py """
    features = tf.parse_single_example(
        example_serialized,
        features={
            'image': tf.FixedLenFeature([], tf.string),
            'gt_boxes': tf.FixedLenFeature([5], tf.int64, default_value=[-1] * 5),
            'dims': tf.FixedLenFeature([2], tf.int64, default_value=[-1] * 2)
        })
    # now return the converted data
    gt_boxes = features['gt_boxes']
    dims = features['dims']
    image = tf.decode_raw(features['image'], tf.float32)
    image = tf.reshape(image, [128, 128])
    return image, tf.cast(gt_boxes, tf.int32), tf.cast(dims, tf.int32)


def print_ckpt_var():
    reader = pywrap_tensorflow.NewCheckpointReader(flags['resnet_restore_file'])
    var_to_shape_map = reader.get_variable_to_shape_map()
    for key in var_to_shape_map:
        print("restore: ", key)


def main():
    file_train = flags['data_directory'] + 'trans_mnist_train.tfrecords'
    x, _, _ = Data.batch_inputs(read_and_decode, file_train, batch_size=flags['batch_size'])
    x = tf.stack([x, x, x], 3)
    with slim.arg_scope(resnet_arg_scope()):
        _ = resnet50(x)
    variables_to_restore = slim.get_model_variables()
    saver = tf_saver.Saver(variables_to_restore)
    with tf.Session() as sess:
        saver.restore(sess, "/home/kd/Documents/tf-Faster-RCNN/Models/resnet_v1_50.ckpt")
        a = input('Now finished restoring...')

if __name__ == '__main__':
    main()
