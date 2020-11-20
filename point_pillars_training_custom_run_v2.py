import os
import time
import numpy as np
import tensorflow as tf
from glob import glob

# from config import Parameters
from config_v2 import Parameters
from loss import PointPillarNetworkLoss
from network import build_point_pillar_graph
# from processors import SimpleDataGenerator
# from custom_processors import CustomDataGenerator
from point_pillars_custom_processors_v2 import CustomDataGenerator
from readers import KittiDataReader

# from point_viz.converter import PointvizConverter

tf.get_logger().setLevel("ERROR")

# DATA_ROOT = "/media/data3/tjtanaa/kitti_dataset/KITTI/object/training"  # TODO make main arg
DATA_ROOT = "/media/data3/tjtanaa/kitti_dataset/"  # TODO make main arg
# MODEL_ROOT = "./logs_Car_Pedestrian_Custom_Dataset_single_process"
# MODEL_ROOT = "./logs_Car_Pedestrian_Custom_Dataset_No_Early_Stopping_wo_Aug_wo_val"
MODEL_ROOT = "./logs_Pedestrian_Custom_Dataset_No_Early_Stopping_wo_Aug_wo_val"

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

if __name__ == "__main__":

    params = Parameters()

    pillar_net = build_point_pillar_graph(params)
    # pillar_net.load_weights(os.path.join(MODEL_ROOT, "model.h5"))

    loss = PointPillarNetworkLoss(params)

    optimizer = tf.keras.optimizers.Adam(lr=params.learning_rate, decay=params.decay_rate)

    pillar_net.compile(optimizer, loss=loss.losses())

    # gt_database_dir = os.path.join(DATA_ROOT, "gt_database")
    gt_database_dir = None

    training_gen = CustomDataGenerator(batch_size=params.batch_size,root_dir = DATA_ROOT,
                    npoints=20000, split='train_val',   classes=list(params.classes_map.keys()), 
                    random_select=True, gt_database_dir=None, aug_hard_ratio=0.7)

    # validation_gen = CustomDataGenerator(batch_size=params.batch_size,  root_dir=DATA_ROOT, 
    #         npoints=20000, split='val',   classes=list(params.classes_map.keys()))


    # save_viz_path = "/home/tan/tjtanaa/PointPillars/visualization/custom_processor"
    # Initialize and setup output directory.
    # Converter = PointvizConverter(save_viz_path)



    # bbox_params = self.convert_labels_into_point_viz_format(gt_boxes3d)
    # print(bbox_params.shape)
    # Converter.compile("custom_sample_{}".format(i), coors=pts_input[:,:3], intensity=pts_input[:,3],
    #                 bbox_params=bbox_params)
        

    log_dir = MODEL_ROOT
    epoch_to_decay = int(
        np.round(params.iters_to_decay / params.batch_size * int(len(training_gen))))
    callbacks = [
        tf.keras.callbacks.TensorBoard(log_dir=log_dir),
        tf.keras.callbacks.ModelCheckpoint(filepath=os.path.join(log_dir, "model.h5"),
                                           monitor='loss', save_best_only=True),
        tf.keras.callbacks.LearningRateScheduler(
            lambda epoch, lr: lr * 0.8 if ((epoch % epoch_to_decay == 0) and (epoch != 0)) else lr, verbose=True),
        # tf.keras.callbacks.EarlyStopping(patience=20, monitor='val_loss'),
    ]

    try:
        pillar_net.fit(training_gen,
                    #    validation_data = validation_gen,
                       steps_per_epoch=len(training_gen),
                       callbacks=callbacks,
                       use_multiprocessing=True,
                       epochs=int(params.total_training_epochs),
                       workers=6)
    except KeyboardInterrupt:
        model_str = "interrupted_%s.h5" % time.strftime("%Y%m%d-%H%M%S")
        pillar_net.save(os.path.join(log_dir, model_str))
        print("Interrupt. Saving output to %s" % os.path.join(os.getcwd(), log_dir[1:], model_str))
