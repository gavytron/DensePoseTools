# to be placed in DensePose/tools
##############################################################################

"""Perform inference on a single image or all images with a certain extension
(e.g., .jpg) in a folder.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import defaultdict
import argparse
import cv2  # NOQA (Must import before importing caffe2 due to bug in cv2)
import glob
import logging
import os
import sys
import time
import pdb
import subprocess
from caffe2.python import workspace

from detectron.core.config import assert_and_infer_cfg
from detectron.core.config import cfg
from detectron.core.config import merge_cfg_from_file
from detectron.utils.io import cache_url
from detectron.utils.logging import setup_logging
from detectron.utils.timer import Timer
import detectron.core.test_engine as infer_engine
import detectron.datasets.dummy_datasets as dummy_datasets
import detectron.utils.c2 as c2_utils
import detectron.utils.vis as vis_utils

c2_utils.import_detectron_ops()

# OpenCL may be enabled by default in OpenCV3; disable it because it's not
# thread safe and causes unwanted GPU memory allocations.
cv2.ocl.setUseOpenCL(False)


def parse_args():
    parser = argparse.ArgumentParser(description='End-to-end inference')
    parser.add_argument(
        '--cfg',
        dest='cfg',
        help='cfg model file (/path/to/model_config.yaml)',
        default=None,
        type=str
    )
    parser.add_argument(
        '--wts',
        dest='weights',
        help='weights model file (/path/to/model_weights.pkl)',
        default=None,
        type=str
    )
    parser.add_argument(
        '--output-dir',
        dest='output_dir',
        help='Directory to keep the output files',
        default='/tmp/infer_vid',
        type=str
    )
    parser.add_argument(
        '--input-file',
        dest='input',
        help='Input video file',
        default=None,
        type=str
    )
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    return parser.parse_args()



def main(args):
    logger = logging.getLogger(__name__)
    merge_cfg_from_file(args.cfg)
    cfg.NUM_GPUS = 1
    args.weights = cache_url(args.weights, cfg.DOWNLOAD_CACHE)
    assert_and_infer_cfg(cache_urls=False)
    model = infer_engine.initialize_model_from_cfg(args.weights)
    dummy_coco_dataset = dummy_datasets.get_coco_dataset()

    print( "capturing video "+args.input)
    cap = cv2.VideoCapture(args.input)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # pdb.set_trace()
    grab =1
    if (cap.isOpened()== False): 
        print("Error opening video stream or file")
        exit
    while (cap.isOpened() and grab <= total_frames):
        grab += 1
        ret_val, im = cap.read()
        #skips intermediate frames
        #if grab%2 !=0:
        #    continue
        #uncomment to resize image
        #im = cv2.resize(im, (int(1280/1),int(720/1)))
        timers = defaultdict(Timer)
        t = time.time()
        with c2_utils.NamedCudaScope(0):
            cls_boxes, cls_segms, cls_keyps, cls_bodys = infer_engine.im_detect_all(
                model, im, None, timers=timers
            )
        output_name = 'frame' + str(grab).zfill(4) + '.mp4'
        print( "| Analysed frame {0} / {1}  in {2}ms".format(grab, total_frames, int(1000.*(time.time() - t))))
        #print('\t | Inference time: {:.3f}s'.format(time.time() - t))
        #for k, v in timers.items():
        #    print('\t | {}: {:.3f}s'.format(k, v.average_time))
        ret = vis_utils.vis_one_image(
            im[:, :, ::-1],  # BGR -> RGB for visualization
            output_name,
            args.output_dir,
            cls_boxes,
            cls_segms,
            cls_keyps,
            cls_bodys,
            dataset=dummy_coco_dataset,
            box_alpha=0.3,
            show_class=False,
            thresh=0.7,
            kp_thresh=2
        )

    cap.release()
    cv2.destroyAllWindows()
#    subprocess.call('ffmpeg -framerate 20 -i {}/file%02d.png -c:v libx264 -r 30 -pix_fmt yuv420p vid/out.mp4'
#                    .format(os.path.join(args.output_dir, 'vid')),
#                     shell=True)
if __name__ == '__main__':
    workspace.GlobalInit(['caffe2', '--caffe2_log_level=0'])
    setup_logging(__name__)
    args = parse_args()
    print(args)
    print(type(args))
    main(args)

