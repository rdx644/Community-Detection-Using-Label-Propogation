# Third-party source notices

`frontend/src/components/CountUp.tsx` was installed as React Bits CountUp-TS-CSS through
the supplied shadcn MCP registry workflow, on 2026-10-14. Source: [React Bits](https://github.com/DavidHDev/react-bits).
The upstream MIT + Commons Clause license is retained verbatim in [REACT_BITS_LICENSE.md](REACT_BITS_LICENSE.md).
Only formatting changes were made to the vendored component. The application wraps it
with saved-metric values, an accessible label and reduced-motion handling.

IBM Plex Sans is distributed via the pinned @fontsource/ibm-plex-sans package. The SIL
Open Font License is retained in [IBM_PLEX_LICENSE.txt](IBM_PLEX_LICENSE.txt). Font assets
are bundled locally; there are no third-party font network requests.

Other dependencies remain installed packages with their original distributed license
notices. Their exact versions and integrity data are recorded in uv.lock, requirements.lock
and frontend/package-lock.json. This repository does not replace third-party licenses.
