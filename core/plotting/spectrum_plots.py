"""Interactive Plotly-based spectrum + mask viewer.

Generates an interactive HTML plot showing:
- Observed Stokes I spectrum
- Observed Stokes V / N1 spectrum
- Mask line positions annotated as vertical tick marks
  (height proportional to line depth)

The function returns a self-contained HTML string that can be embedded
directly in a page or served as a standalone response.
"""


def plot_spectrum_with_mask(obs, line_mask, output_path=''):
    """Build an interactive Plotly figure of the observed spectrum with mask annotations.

    Parameters
    ----------
    obs : observation
        Loaded observation object with wl, specI, specV, specN1, specSig arrays.
    line_mask : mask
        Loaded mask object with wl, depth, element, lande arrays.
    output_path : str
        If non-empty, write the self-contained HTML file to this path.

    Returns
    -------
    str
        Self-contained HTML string for the interactive Plotly figure.
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as exc:
        raise ImportError(
            'plotly is required for interactive spectrum plots. '
            'Install it with: pip install plotly'
        ) from exc

    import numpy as np

    obs_wl = obs.wl.round(4)
    obs_i = obs.specI.round(5)
    obs_v = obs.specV.round(5)
    obs_n1 = obs.specN1.round(5)
    obs_sig = obs.specSig.round(5)

    mask_wl = line_mask.wl
    mask_depth = line_mask.depth
    mask_element = line_mask.element

    # Determine the wavelength range that overlaps with the spectrum
    wl_min = float(obs_wl[0]) if len(obs_wl) > 0 else 0.0
    wl_max = float(obs_wl[-1]) if len(obs_wl) > 0 else 1.0

    # Filter mask lines to observed wavelength range (with a small margin)
    margin = (wl_max - wl_min) * 0.02
    in_range = (mask_wl >= wl_min - margin) & (mask_wl <= wl_max + margin)
    mask_wl_vis = mask_wl[in_range]
    mask_depth_vis = mask_depth[in_range]
    mask_element_vis = mask_element[in_range]

    # Normalise depths for display: scale so max depth fills ~0.3 of the plot
    max_depth = float(np.max(mask_depth_vis)) if len(mask_depth_vis) > 0 else 1.0
    max_depth = max(max_depth, 1e-6)

    # Build element labels (encoded as float: integer=atomic_number, decimal=ion*0.01)
    def _element_label(enc):
        Z = int(round(enc))
        ion_decimal = round((enc - Z) * 100)
        ion_str = ['I', 'II', 'III', 'IV', 'V']
        ion_label = ion_str[min(ion_decimal, 4)] if ion_decimal >= 0 else '?'
        return f'Z={Z} {ion_label}'

    mask_labels = [_element_label(e) for e in mask_element_vis]

    # ── Build subplot layout: Stokes I (top), V (middle), N1 (bottom) ──────────
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=['Stokes I', 'Stokes V', 'Null (N1)'],
        row_heights=[3, 1.5, 1.5],
    )

    # — Stokes I panel ——————————————————————————————————————————————————
    fig.add_trace(
        go.Scatter(
            x=obs_wl, y=obs_i,
            mode='lines',
            name='I/Ic',
            line=dict(color='#181d26', width=1.2),
            hovertemplate='λ=%{x:.4f} nm<br>I=%{y:.5f}<extra></extra>',
        ),
        row=1, col=1,
    )

    # Error band for I
    i_upper = obs_i + obs_sig
    i_lower = obs_i - obs_sig
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([obs_wl, obs_wl[::-1]]),
            y=np.concatenate([i_upper, i_lower[::-1]]),
            fill='toself',
            fillcolor='rgba(24,29,38,0.12)',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip',
            name='I σ',
        ),
        row=1, col=1,
    )

    # Mask line ticks on Stokes I panel — drawn as small vertical segments
    # positioned just below the continuum level (y ~ 1.0 area)
    if len(mask_wl_vis) > 0:
        # Compute y baseline: just below the minimum of the spectrum in range
        y_base = float(np.min(obs_i)) - 0.05
        # Each tick has height proportional to line depth
        tick_scale = 0.20  # max tick height as fraction of the I range
        i_range = float(np.max(obs_i)) - float(np.min(obs_i))
        i_range = max(i_range, 0.01)

        tick_x = []
        tick_y = []
        for wl_m, d in zip(mask_wl_vis, mask_depth_vis):
            tick_height = (d / max_depth) * tick_scale * i_range
            tick_x += [float(wl_m), float(wl_m), None]
            tick_y += [y_base, y_base - tick_height, None]

        fig.add_trace(
            go.Scatter(
                x=tick_x, y=tick_y,
                mode='lines',
                name='Mask lines',
                line=dict(color='rgba(27,97,201,0.60)', width=1.0),
                hoverinfo='skip',
                showlegend=True,
            ),
            row=1, col=1,
        )

        # Invisible scatter for hover tooltips on mask lines
        fig.add_trace(
            go.Scatter(
                x=mask_wl_vis,
                y=np.full(len(mask_wl_vis), y_base),
                mode='markers',
                name='Mask (hover)',
                marker=dict(size=4, color='rgba(27,97,201,0.4)', symbol='line-ns-open'),
                customdata=list(zip(mask_depth_vis, mask_labels)),
                hovertemplate=(
                    'λ=%{x:.4f} nm<br>'
                    'depth=%{customdata[0]:.3f}<br>'
                    '%{customdata[1]}<extra>mask line</extra>'
                ),
                showlegend=False,
            ),
            row=1, col=1,
        )

    # — Stokes V panel ——————————————————————————————————————————————————
    fig.add_trace(
        go.Scatter(
            x=obs_wl, y=obs_v,
            mode='lines',
            name='V/Ic',
            line=dict(color='#1b61c9', width=1.0),
            hovertemplate='λ=%{x:.4f} nm<br>V=%{y:.5f}<extra></extra>',
        ),
        row=2, col=1,
    )
    fig.add_hline(y=0, line=dict(color='#e0e2e6', width=1, dash='dot'), row=2, col=1)

    # — Null (N1) panel ——————————————————————————————————————————————————
    fig.add_trace(
        go.Scatter(
            x=obs_wl, y=obs_n1,
            mode='lines',
            name='N1/Ic',
            line=dict(color='#6b7280', width=1.0),
            hovertemplate='λ=%{x:.4f} nm<br>N1=%{y:.5f}<extra></extra>',
        ),
        row=3, col=1,
    )
    fig.add_hline(y=0, line=dict(color='#e0e2e6', width=1, dash='dot'), row=3, col=1)

    # ── Layout ──────────────────────────────────────────────────────────────────
    fig.update_layout(
        height=700,
        margin=dict(l=60, r=20, t=60, b=50),
        plot_bgcolor='#ffffff',
        paper_bgcolor='#f8fafc',
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                  size=12, color='#181d26'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        hovermode='x unified',
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor='#e0e2e6',
        gridwidth=0.5,
        zeroline=False,
        showline=True,
        linecolor='#e0e2e6',
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#e0e2e6',
        gridwidth=0.5,
        zeroline=False,
        showline=True,
        linecolor='#e0e2e6',
    )

    # x-axis label on last row
    fig.update_xaxes(title_text='Wavelength (nm)', row=3, col=1)
    fig.update_yaxes(title_text='I/Ic', row=1, col=1)
    fig.update_yaxes(title_text='V/Ic', row=2, col=1)
    fig.update_yaxes(title_text='N1/Ic', row=3, col=1)

    html = fig.to_html(full_html=True, include_plotlyjs='cdn', config={'scrollZoom': True})

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as fh:
            fh.write(html)

    return html
