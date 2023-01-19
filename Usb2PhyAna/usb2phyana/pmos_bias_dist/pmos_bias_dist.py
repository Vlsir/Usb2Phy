""" 
# Pmos Bias Distribution
"""

# Hdl Imports
import hdl21 as h


@h.paramclass
class Params:
    pbias = h.Param(dtype=h.Instantiable, desc="Unit Bias Pmos Device")
    pcasc = h.Param(dtype=h.Instantiable, desc="Unit Cascode Pmos Device")
    pcdiode = h.Param(dtype=h.Instantiable, desc="Cascode-Diode Pmos Device")
    taps = h.Param(dtype=tuple, desc="Output weights")
    # iin = h.Param(dtype=h.Scalar, desc="Input Bias Current (A)")


@h.generator
def PmosBiasDist(params: Params) -> h.Module:
    """# Pmos-Side Cascode Bias Distribution"""

    @h.module
    class PmosBiasDist:
        """Bias Distribution"""

        # IO Interface
        VDD, VSS = h.Ports(2)
        iin_casc, iin_top = h.Inputs(2, desc="Input Bias Currents")

        # Parametric Output Bus. One per entry in `params.taps`
        iout = h.Output(width=len(params.taps), desc="Output Current(s) Bus")

        ### Pmos cascode diode
        pcdiode = params.pcdiode(g=iin_casc, d=iin_casc, s=VDD, VDD=VDD, VSS=VSS)

        ### Pmos bias diode, with cascode
        pdiode = params.pbias(g=iin_top, s=VDD, VDD=VDD, VSS=VSS)
        pdiode_casc = params.pcasc(s=pdiode.d, g=iin_casc, d=iin_top, VDD=VDD, VSS=VSS)

    # Create a few shorthand names
    P = PmosBiasDist
    VDD, VSS = P.VDD, P.VSS

    P.outds = h.Signal(width=len(params.taps))
    # Add each output leg
    for (idx, weight) in enumerate(params.taps):
        pb = P.add(  # Weighted top bias pmos
            name=f"pbias{idx}",
            val=weight
            * params.pbias(g=P.iin_top, d=P.outds[idx], s=VDD, VDD=VDD, VSS=VSS),
        )
        P.add(  # Weighted cascode
            name=f"pcasc{idx}",
            val=weight
            * params.pcasc(
                d=P.iout[idx], g=P.iin_casc, s=P.outds[idx], VDD=VDD, VSS=VSS
            ),
        )

    return P
