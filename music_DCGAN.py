""" Deep Convolutional Generative Adversarial Network (DCGAN).
Using deep convolutional generative adversarial networks (DCGAN) to generate
digit images from a noise distribution.
References:
    - Unsupervised representation learning with deep convolutional generative
    adversarial networks. A Radford, L Metz, S Chintala. arXiv:1511.06434.
Links:
    - [DCGAN Paper](https://arxiv.org/abs/1511.06434).
    - [MNIST Dataset](http://yann.lecun.com/exdb/mnist/).
Author: Aymeric Damien
Project: https://github.com/aymericdamien/TensorFlow-Examples/

Nice visualisations of convolutions:
https://github.com/vdumoulin/conv_arithmetic

Nice blog posts:
- https://medium.com/@mozesr/deep-convolutional-gans-notes-746d891056d7
- https://towardsdatascience.com/types-of-convolutions-in-deep-learning-717013397f4d

Example of convolutions and transposed convolutions:
https://www.programcreek.com/python/example/94702/tensorflow.contrib.layers.conv2d_transpose

"""

from __future__ import division, print_function, absolute_import

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import os
import pickle

# Import MNIST data
# from tensorflow.examples.tutorials.mnist import input_data
# mnist = input_data.read_data_sets("/tmp/data/", one_hot=True)
# load data
rows = []
columns = []
with open('saved_data' + os.sep + 'data_tower.pickle', 'rb') as handle:
    d = pickle.load(handle)
    serialised_segments = d['serialised_segments']
    rows = d['rows']
    columns = d['columns']

np.random.shuffle( serialised_segments )

# Training Params
num_steps = 20000
batch_size = 128

# __MAX__
# split in batches
batches_train = []
batches_test = []
tmp_counter = 1
batch_idx_start = 0
batch_idx_end = batch_idx_start + batch_size
while batch_idx_end < serialised_segments.shape[0]:
    # decide whether to put it in test or train
    if tmp_counter%10 == 0:
        batch_idx_end = batch_idx_start + 4
        batches_test.append( serialised_segments[ batch_idx_start:batch_idx_end,: ] )
        batch_idx_start += 4
        batch_idx_end = batch_idx_start + batch_size
    else:
        batch_idx_end = batch_idx_start + batch_size
        batches_train.append( serialised_segments[ batch_idx_start:batch_idx_end,: ] )
        batch_idx_start += batch_size
    tmp_counter += 1

# Network Parameters
image_dim = rows*columns # MNIST images are 28x28 pixels
gen_hidden_dim = 256
disc_hidden_dim = 256
noise_dim = 200 # Noise data points


# Generator Network
# Input: Noise, Output: Image
def generator(x, reuse=False):
    with tf.variable_scope('Generator', reuse=reuse):
        # TensorFlow Layers automatically create variables and calculate their
        # shape, based on the input.
        x = tf.layers.dense(x, units= (int(np.floor(rows/4))-1) * (int(np.floor(columns/4))-1) * 128)
        x = tf.nn.tanh(x)
        # Reshape to a 4-D array of images: (batch, height, width, channels)
        # New shape: (batch, 15, 15, 128)
        x = tf.reshape(x, shape=[-1, int(np.floor(rows/4))-1, int(np.floor(columns/4))-1, 128])
        # Deconvolution, image shape: (batch, 32, 32, 64)
        x = tf.layers.conv2d_transpose(x, 64, [4,4], strides=2)
        # Deconvolution, image shape: (batch, 65, 64, 1)
        x = tf.layers.conv2d_transpose(x, 1, [3,2], strides=2)
        # Apply sigmoid to clip values between 0 and 1
        x = tf.nn.sigmoid(x)
        return x


# Discriminator Network
# Input: Image, Output: Prediction Real/Fake Image
def discriminator(x, reuse=False):
    with tf.variable_scope('Discriminator', reuse=reuse):
        # Typical convolutional neural network to classify images.
        x = tf.layers.conv2d(x, 64, 5)
        x = tf.nn.tanh(x)
        x = tf.layers.average_pooling2d(x, 2, 2)
        x = tf.layers.conv2d(x, 128, 5)
        x = tf.nn.tanh(x)
        x = tf.layers.average_pooling2d(x, 2, 2)
        x = tf.contrib.layers.flatten(x)
        x = tf.layers.dense(x, 1024)
        x = tf.nn.tanh(x)
        # Output 2 classes: Real and Fake images
        x = tf.layers.dense(x, 2)
    return x

# Build Networks
# Network Inputs
noise_input = tf.placeholder(tf.float32, shape=[None, noise_dim])
real_image_input = tf.placeholder(tf.float32, shape=[None, rows, columns, 1])

# Build Generator Network
gen_sample = generator(noise_input)

# Build 2 Discriminator Networks (one from noise input, one from generated samples)
disc_real = discriminator(real_image_input)
disc_fake = discriminator(gen_sample, reuse=True)
disc_concat = tf.concat([disc_real, disc_fake], axis=0)

# Build the stacked generator/discriminator
stacked_gan = discriminator(gen_sample, reuse=True)

# Build Targets (real or fake images)
disc_target = tf.placeholder(tf.int32, shape=[None])
gen_target = tf.placeholder(tf.int32, shape=[None])

# Build Loss
disc_loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(
    logits=disc_concat, labels=disc_target))
gen_loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(
    logits=stacked_gan, labels=gen_target))

# Build Optimizers
optimizer_gen = tf.train.AdamOptimizer(learning_rate=0.001)
optimizer_disc = tf.train.AdamOptimizer(learning_rate=0.001)

# Training Variables for each optimizer
# By default in TensorFlow, all variables are updated by each optimizer, so we
# need to precise for each one of them the specific variables to update.
# Generator Network Variables
gen_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='Generator')
# Discriminator Network Variables
disc_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='Discriminator')

# Create training operations
train_gen = optimizer_gen.minimize(gen_loss, var_list=gen_vars)
train_disc = optimizer_disc.minimize(disc_loss, var_list=disc_vars)

# Initialize the variables (i.e. assign their default value)
init = tf.global_variables_initializer()

# Start training
with tf.Session() as sess:

    # Run the initializer
    sess.run(init)

    # __MAX__
    batch_idx = 0
    for i in range(1, num_steps+1):

        # Prepare Input Data
        # Get the next batch of MNIST data (only images are needed, not labels)
        batch_x = batches_train[ batch_idx ]
        batch_x = np.reshape(batch_x, newshape=[-1, rows, columns, 1])
        batch_idx += 1
        batch_idx = batch_idx%len(batches_train)
        # Generate noise to feed to the generator
        z = np.random.uniform(-1., 1., size=[batch_size, noise_dim])

        # Prepare Targets (Real image: 1, Fake image: 0)
        # The first half of data fed to the generator are real images,
        # the other half are fake images (coming from the generator).
        batch_disc_y = np.concatenate(
            [np.ones([batch_size]), np.zeros([batch_size])], axis=0)
        # Generator tries to fool the discriminator, thus targets are 1.
        batch_gen_y = np.ones([batch_size])

        # Training
        feed_dict = {real_image_input: batch_x, noise_input: z,
                     disc_target: batch_disc_y, gen_target: batch_gen_y}
        _, _, gl, dl = sess.run([train_gen, train_disc, gen_loss, disc_loss],
                                feed_dict=feed_dict)
        if i % 100 == 0 or i == 1:
            print('Step %i: Generator Loss: %f, Discriminator Loss: %f' % (i, gl, dl))

    # Generate images from noise, using the generator network.
    f, a = plt.subplots(4, 10, figsize=(10, 4))
    for i in range(10):
        # Noise input.
        z = np.random.uniform(-1., 1., size=[4, noise_dim])
        g = sess.run(gen_sample, feed_dict={noise_input: z})
        print('g.shape: ', g.shape)
        for j in range(4):
            # Generate image from noise. Extend to 3 channels for matplot figure.
            img = np.reshape(np.repeat(g[j][:, :, np.newaxis], 3, axis=2),
                             newshape=(rows, columns, 3))
            a[j][i].imshow(img)

    # f.show()
    plt.draw()
    plt.savefig('figs/DCGAN_music.png', dpi=300); plt.clf()
    # plt.waitforbuttonpress()