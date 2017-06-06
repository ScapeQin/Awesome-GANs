from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import time
import began

import sys
sys.path.insert(0, '../')

from datasets import DataIterator, DataSet
import image_utils as iu


dirs = {
    'sample_output': './BEGAN/',
    'checkpoint': './model/checkpoint',
    'model': './model/BEGAN-model.ckpt'
}
paras = {
    'epoch': 250,
    'batch_size': 16,
    'logging_interval': 1000
}


def main():
    start_time = time.time()  # clocking start

    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.95)
    config = tf.ConfigProto(allow_soft_placement=True, gpu_options=gpu_options)

    with tf.Session(config=config) as s:
        end_time = time.time() - start_time

        # BEGAN Model
        model = began.BEGAN(s)

        # initializing
        s.run(tf.global_variables_initializer())

        # load model & graph & weight
        ckpt = tf.train.get_checkpoint_state('./model/')
        if ckpt and ckpt.model_checkpoint_path:
            # Restores from checkpoint
            model.saver.restore(s, ckpt.model_checkpoint_path)

            global_step = ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1]
            print("[+] global step : %s" % global_step, " successfully loaded")
        else:
            global_step = 0
            print('[-] No checkpoint file found')
            # return

        # initializing variables
        tf.global_variables_initializer().run()

        # loading Celeb-A dataset
        ds = DataSet(input_height=64,
                     input_width=64,
                     input_channel=3,
                     dataset_name="celeb-a")
        images = ds.images

        sample_z = np.random.uniform(-1., 1., size=(model.sample_num, model.z_dim)).astype(np.float32)

        d_overpowered = False
        kt = tf.Variable(0., dtype=tf.float32)  # init K_0 value, 0

        batch_per_epoch = int(len(images) / paras['batch_size'])
        for epoch in range(paras['epoch']):
            for step in range(batch_per_epoch):
                iter_ = datasets.DataIterator([images], paras['batch_size'])

                # k_t update
                # k_t+1 = K_t + lambda_k * (gamma * d_real - d_fake)
                kt = kt + model.lambda_k * (model.gamma * model.D_real - model.D_fake)

                # z update
                batch_z = np.random.uniform(-1., 1., [paras['batch_size'], model.z_dim]).astype(np.float32)

                # update D network
                if not d_overpowered:
                    s.run(model.d_op, feed_dict={model.x: 0,
                                                 model.z: batch_z,
                                                 model.kt: kt})

                # update G network
                s.run(model.g_op, feed_dict={model.z: batch_z,
                                             model.kt: kt})

                if global_step % paras['logging_interval'] == 0:
                    batch_z = np.random.uniform(-1., 1., [paras['batch_size'], model.z_dim]).astype(np.float32)

                    d_loss, g_loss, summary = s.run([
                        model.d_loss,
                        model.g_loss,
                        model.merged
                    ], feed_dict={
                        model.x: 0,
                        model.z: batch_z
                    })

                    # print loss
                    print("[+] Epoch %03d Step %05d => " % (epoch, step),
                          "D loss : {:.8f}".format(d_loss), " G loss : {:.8f}".format(g_loss))

                    # update overpowered
                    d_overpowered = d_loss < g_loss / 3

                    # training G model with sample image and noise
                    samples = s.run(model.G, feed_dict={
                        model.x: 0,
                        model.z: sample_z
                    })

                    # summary saver
                    model.writer.add_summary(summary, step)

                    # export image generated by model G
                    sample_image_height = model.sample_size
                    sample_image_width = model.sample_size
                    sample_dir = dirs['sample_output'] + 'train_{0}_{1}.png'.format(epoch, step)

                    # Generated image save
                    iu.save_images(samples, size=[sample_image_height, sample_image_width], image_path=sample_dir)

                    # model save
                    model.saver.save(s, dirs['model'], global_step=step)

                global_step += 1

    # elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))

    # close tf.Session
    s.close()

if __name__ == '__main__':
    main()
