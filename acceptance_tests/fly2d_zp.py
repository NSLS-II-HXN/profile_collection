def test_fly2d():
    """
    Test ``fly2d`` scan with ZP motors.
    """
    RE(fly2d([sclr1,zebra,merlin1,xspress3],zpssx,-1,1,10,zpssy,-1,1,10,0.03))
