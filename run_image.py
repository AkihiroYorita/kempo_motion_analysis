import argparse
import logging
import sys
import time
import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
# import importlib
# tf_pose_estimation = importlib.import_module("tf-pose-estimation")

from tf_pose import common
from tf_pose.estimator import TfPoseEstimator
from tf_pose.networks import get_graph_path, model_wh

from motion_analysis import MotionAnalysis

logger = logging.getLogger('TfPoseEstimator')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='tf-pose-estimation run')
    parser.add_argument('--image', type=str, default='./images/p1.jpg')
    parser.add_argument('--model', type=str, default='cmu', help='cmu / mobilenet_thin')

    parser.add_argument('--resize', type=str, default='"432x368"',
                        help='if provided, resize images before they are processed. '
                             'default=0x0, Recommends : 432x368 or 656x368 or 1312x736 ')
    parser.add_argument('--resize-out-ratio', type=float, default=4.0,
                        help='if provided, resize heatmaps before they are post-processed. default=1.0')
    parser.add_argument('--plt_network', type=bool, default=False)
    parser.add_argument('--path', type=str, default="")
    parser.add_argument('--cog', type=bool, default=False)
    args = parser.parse_args()

    w, h = model_wh(args.resize)
    if w == 0 or h == 0:
        e = TfPoseEstimator(get_graph_path(args.model), target_size=(432, 368))
    else:
        e = TfPoseEstimator(get_graph_path(args.model), target_size=(w, h))

    path_image = os.path.join(args.path, args.image)
    path_out = args.path

    # estimate human poses from a single image !
    image = common.read_imgfile(path_image, None, None)
    logger.debug('shape of image: '+ str(image.shape))
    h_pxl, w_pxl = image.shape[0], image.shape[1]
    print(w_pxl, h_pxl)
    if image is None:
        logger.error('Image can not be read, path=%s' % path_image)
        sys.exit(-1)

    t = time.time()
    humans = e.inference(image, resize_to_default=(w > 0 and h > 0), upsample_size=args.resize_out_ratio)
    elapsed = time.time() - t
    logger.info('inference image: %s in %.4f seconds.' % (path_image, elapsed))

    bodies_cog = [[0,0,0]]
    if args.cog:
        ma = MotionAnalysis()
        bodies_cog = ma.multi_bodies_cog(humans=humans)

    image = TfPoseEstimator.draw_humans(image, humans, imgcopy=False)
    if not args.plt_network:
        fig = plt.figure()
        plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        if args.cog:
            bodies_cog = bodies_cog[~np.isnan(bodies_cog[:, 18, 1])]
            # bodies_cog = bodies_cog[~np.isnan(bodies_cog[:,:,1])]
            plt.scatter(bodies_cog[:, 0] * w_pxl, bodies_cog[:, 1] * h_pxl, color='black', marker='o', s=5)
        bgimg = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_BGR2RGB)
        bgimg = cv2.resize(bgimg, (e.heatMat.shape[1], e.heatMat.shape[0]), interpolation=cv2.INTER_AREA)
        plt.savefig(os.path.join(path_out,
                                 args.image.split('.')[-2] + "_estimated.png"))
        plt.show()
    else:
        fig = plt.figure()
        a = fig.add_subplot(2, 2, 1)
        a.set_title('Result')
        plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        plt.plot()
        bgimg = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_BGR2RGB)
        bgimg = cv2.resize(bgimg, (e.heatMat.shape[1], e.heatMat.shape[0]), interpolation=cv2.INTER_AREA)

        # show network output
        a = fig.add_subplot(2, 2, 2)
        plt.imshow(bgimg, alpha=0.5)
        tmp = np.amax(e.heatMat[:, :, :-1], axis=2)
        plt.imshow(tmp, cmap=plt.cm.gray, alpha=0.5)
        plt.colorbar()

        tmp2 = e.pafMat.transpose((2, 0, 1))
        tmp2_odd = np.amax(np.absolute(tmp2[::2, :, :]), axis=0)
        tmp2_even = np.amax(np.absolute(tmp2[1::2, :, :]), axis=0)

        a = fig.add_subplot(2, 2, 3)
        a.set_title('Vectormap-x')
        # plt.imshow(CocoPose.get_bgimg(inp, target_size=(vectmap.shape[1], vectmap.shape[0])), alpha=0.5)
        plt.imshow(tmp2_odd, cmap=plt.cm.gray, alpha=0.5)
        plt.colorbar()

        a = fig.add_subplot(2, 2, 4)
        a.set_title('Vectormap-y')
        # plt.imshow(CocoPose.get_bgimg(inp, target_size=(vectmap.shape[1], vectmap.shape[0])), alpha=0.5)
        plt.imshow(tmp2_even, cmap=plt.cm.gray, alpha=0.5)
        plt.colorbar()
        plt.show()
