import torch
from cutout_model.model import UNet


def test_unet_shape_and_size():
    model = UNet()
    assert model(torch.zeros(2, 4, 64, 64)).shape == (2, 1, 64, 64)
    count = sum(p.numel() for p in model.parameters())
    assert 7_000_000 < count < 9_000_000


def test_unet_takes_the_real_input_size():
    assert UNet()(torch.zeros(1, 4, 320, 320)).shape == (1, 1, 320, 320)


def test_unet_head_is_a_one_by_one_conv():
    head = UNet().head
    assert isinstance(head, torch.nn.Conv2d) and head.kernel_size == (1, 1) and head.out_channels == 1
