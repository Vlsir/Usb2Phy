import amaranth as am
from amaranth.lib.fifo import AsyncFIFO

class SimpleBus:
    """
    A simple unidirectional data/valid bus with optional ready signal

    Parameters
    ----------
    width : int
        Datapath width
    ready_signal : bool
        Indicates weather this part of the bus can backup transactions

    Attributes
    ----------
    data : am.Signal(width), (out, in)
        Data signal
    valid : am.Signal, (out, in)
        Valid signal
    ready : am.Signal or NoneType, (in, out)
        Ready signal
    """
    def __init__(self, width, ready_signal = False):
        self.data = am.Signal(width)
        self.valid = am.Signal()

        self.ready = am.Signal() if ready_signal else None

        self.__width = width
        self.__ready_signal = ready_signal

    def drive(self, domain, bus):
        assert self.__ready_signal == bus.__ready_signal
        assert self.__width == bus.__width

        domain += bus.data.eq(self.data)
        domain += bus.valid.eq(self.valid)
        if self.__ready_signal:
            domain += self.ready.eq(bus.ready)

class Sr(am.Elaboratable):
    def __init__(self, length):
        self.chain = am.Signal(length)
        self.input = am.Signal()
        self.output = am.Signal()
        self.__length = length

    def elaborate(self, platform):
        m = am.Module()

        m.d.sync += self.chain[0].eq(self.input)
        m.d.comb += self.output.eq(self.chain[-1])

        for i in range(1, self.__length):
            m.d.sync += self.chain[i].eq(self.chain[i - 1])

        return m

class SrP(am.Elaboratable):
    def __init__(self, length):
        self.chain = am.Signal(length)
        self.load = am.Signal()
        self.output = am.Signal()

    def elaborate(self, platform):
        pass

class Ser(am.Elaboratable):
    def __init__(self, ser_domain, par_domain, gearing = 8, depth = 2):
        self.ser_domain = ser_domain
        self.par_domain = par_domain

        pass

    def elaborate(self, platform):
        pass


