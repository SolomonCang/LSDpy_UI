"""Basic plotting functions for LSD products.

These utilities are intentionally lightweight and optional.
They import matplotlib only when a plot function is called.
"""


def _import_pyplot():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            'matplotlib is required for plotting. Install it with: pip install matplotlib'
        ) from exc
    return plt


def plot_lsd_profile(profile, output_path='', show=True):
    """Plot Stokes V, N1, and I from a `prof`-like object.

    Expected attributes on `profile`:
    - vel
    - specV, specSigV
    - specN1, specSigN1
    - specI, specSigI
    """
    plt = _import_pyplot()

    fig, (ax1, ax2,
          ax3) = plt.subplots(3,
                              sharex=True,
                              gridspec_kw={'height_ratios': [1, 1, 3]})

    ax1.errorbar(profile.vel,
                 profile.specV,
                 yerr=profile.specSigV,
                 fmt='none',
                 ecolor='r',
                 alpha=0.35)
    ax1.plot(profile.vel, profile.specV, 'r-', lw=1.0)
    ax1.axhline(0.0, ls='--', c='k', alpha=0.5)
    ax1.set_ylabel('V/Ic')

    ax2.errorbar(profile.vel,
                 profile.specN1,
                 yerr=profile.specSigN1,
                 fmt='none',
                 ecolor='m',
                 alpha=0.35)
    ax2.plot(profile.vel, profile.specN1, 'm-', lw=1.0)
    ax2.axhline(0.0, ls='--', c='k', alpha=0.5)
    ax2.set_ylabel('N/Ic')

    ax3.errorbar(profile.vel,
                 1.0 - profile.specI,
                 yerr=profile.specSigI,
                 fmt='none',
                 ecolor='b',
                 alpha=0.35)
    ax3.plot(profile.vel, 1.0 - profile.specI, 'b-', lw=1.2)
    ax3.axhline(1.0, ls='--', c='k', alpha=0.5)
    ax3.set_ylabel('I/Ic')
    ax3.set_xlabel('Velocity (km/s)')

    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    return fig


def plot_observation_vs_model(wavelength,
                              obs_i,
                              model_i,
                              output_path='',
                              show=True):
    """Plot observed and model Stokes I spectrum in wavelength space."""
    plt = _import_pyplot()

    fig, ax = plt.subplots(1, 1)
    ax.plot(wavelength, obs_i, color='k', lw=1.0, label='Observed I/Ic')
    ax.plot(wavelength, model_i, color='tab:blue', lw=1.0, label='Model I/Ic')
    ax.set_xlabel('Wavelength')
    ax.set_ylabel('I/Ic')
    ax.legend(loc='best')
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    return fig
