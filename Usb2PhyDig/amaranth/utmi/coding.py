import amaranth as am

class SerNRZIDec(am.Elaboratable):
    """
    Serial NRZI decoder

    Parameters
    ----------
    pipeline : bool
        Optionally pipeline this stage

    Attributes
    ----------
    din : am.Signal, in
        The input data where the J line state is represented by a 1
        and the K by a zero
    dout : am.Signal, out
        The output NRZI decoded data
    idle : am.Signal, in
        Should be asserted when the bus is in an idle state
    bypass : am.Signal, in
        Bypass the decoder (pipe in to out with the same delay)
    """
    def __init__(self, pipeline = False):
        self.din = am.Signal()
        self.dout = am.Signal(reset_less = True)

        self.idle = am.Signal()
        self.bypass = am.Signal()

        # State tracking
        self.last = am.Signal(reset_less = True)

        self.__pipeline = pipeline

    def elaborate(self, platform):
        m = am.Module()

        m.d.sync += self.last.eq(self.din | self.idle)

        with m.If(self.bypass):
            if self.__pipeline:
                m.d.sync += self.dout.eq(self.din)
            else:
                m.d.comb += self.dout.eq(self.din)
        with m.Else():
            if self.__pipeline:
                m.d.sync += self.dout.eq(~(self.last ^ self.din))
            else:
                m.d.comb += self.dout.eq(~(self.last ^ self.din))

        return m

class SerNRZIEnc(am.Elaboratable):
    """
    Serial NRZI Encoder

    Parameters
    ----------
    pipeline : bool
        Optionally pipeline this stage

    Attributes
    ----------
    din : am.Signal, in
        The input uncoded data
    dout : am.Signal, out
        The output NRZI encoded data where J is represented by a 1
        and K by a zero
    idle : am.Signal, in
        Should be asserted when the bus is in an idle state
    bypass : am.Signal, in
        Bypass the encoder (pipe in to out with the same delay)
    """
    def __init__(self, pipeline = False):
        self.din = am.Signal()
        self.dout = am.Signal(reset_less = True)

        self.idle = am.Signal()
        self.bypass = am.Signal()

        # State tracking
        self.last = am.Signal(reset_less = True)

        self.__pipeline = pipeline

    def elaborate(self, platform):
        m = am.Module()

        with m.If(self.idle):
            m.d.sync += self.last.eq(1)
        with m.Else():
            m.d.sync += self.last.eq(self.last == self.din)

        with m.If(self.bypass):
            if self.__pipeline:
                m.d.sync += self.dout.eq(self.din)
            else:
                m.d.comb += self.dout.eq(self.din)
        with m.Else():
            if self.__pipeline:
                m.d.sync += self.dout.eq(self.last == self.din)
            else:
                m.d.comb += self.dout.eq(self.last == self.din)

        return m

class ParNRZIDec(am.Elaboratable):
    """
    A parallel NRZI decoder

    Parameters
    ----------
    width : int
        The width of the parallel bus
    pipeline : bool
        Optionally pipeline this stage

    Attributes
    ----------
    din : am.Signal(width), in
        Input encoded parallel databus
    dout : am.Signal(width), out
        Output decoded parallel databus
    din_valid : am.Signal, in
        Should be asserted when the input data is valid new data
    dout_valid : am.Signal, out
        Will be asserted when the output data is new valid data
    idle : am.Signal, in
        Should be asserted when the bus goes idle and deasserted the first time
        valid is asserted in a given transaction
    bypass : am.Signal, in
        Should pipe din to dout with the standard latency
    """
    def __init__(self, width = 8, pipeline = False):
        self.din = am.Signal(width)
        self.dout = am.Signal(width, reset_less=True)

        self.din_valid = am.Signal()
        self.dout_valid = am.Signal()
        self.idle = am.Signal()

        self.bypass = am.Signal()

        self.carry = am.Signal(reset_less=True)
        self.__width = width
        self.__pipeline = pipeline

    def elaborate(self, platform):
        m = am.Module()

        d = m.d.sync if self.__pipeline else m.d.comb

        with m.If(self.idle):
            m.d.sync += self.carry.eq(1)
        with m.If(self.din_valid):
            m.d.sync += self.carry.eq(self.din[-1])
        d += self.dout_valid.eq(self.din_valid)
        d += self.dout[0].eq(self.carry == self.din[0])
        for i in range(1, self.__width):
            d += self.dout[i].eq(self.din[i - 1] == self.din[i])

        return m

class ParNRZIEnc(am.Elaboratable):
    """
    A parallel NRZI encoder

    NOTE: 

    Parameters
    ----------
    width : int
        The width of the parallel bus
    pipeline : bool
        Optionally pipeline this stage

    Attributes
    ----------
    din : am.Signal(width), in
        Input encoded parallel databus
    dout : am.Signal(width), out
        Output decoded parallel databus
    din_valid : am.Signal, in
        Should be asserted when the input data is valid new data
    dout_valid : am.Signal, out
        Will be asserted when the output data is valid new data
    idle : am.Signal, in
        Should be asserted when the bus goes idle and deasserted the first time
        valid is asserted in a given transaction
    bypass : am.Signal, in
        Should pipe din to dout with the standard latency
    """
    def __init__(self, width = 8, pipeline = False):
        self.din = am.Signal(width)
        self.dout = am.Signal(width, reset_less=True)

        self.din_valid = am.Signal()
        self.dout_valid = am.Signal(reset_less=True)
        self.idle = am.Signal()

        self.bypass = am.Signal()

        self.carry = am.Signal(reset_less=True)
        self.__width = width
        self.__pipeline = pipeline

    def elaborate(self, platform):
        m = am.Module()

        d = m.d.sync if self.__pipeline else m.d.comb

        with m.If(self.idle):
            m.d.sync += self.carry.eq(1)
        with m.If(self.din_valid):
            m.d.sync += self.carry.eq(self.din[-1])
        d += self.dout_valid.eq(self.din_valid)
        d += self.dout[0].eq(self.carry == self.din[0])
        for i in range(1, self.__width):
            d += self.dout[i].eq(self.din[i - 1] == self.din[i])

        return m

class ParBitStuff(am.Elaboratable):
    pass
