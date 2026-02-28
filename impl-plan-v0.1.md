# Serverless, Infra-Agnostic IIIF Image Server — Implementation Summary (Export Doc)

This document summarizes what your service **must** implement to be compliant with the **IIIF Image API**, and what is **recommended/optional for production**, with explicit mapping to **IIIF Image API 3.0 compliance levels (0/1/2)**.

Primary references:
- IIIF Image API 3.0 spec: :contentReference[oaicite:0]{index=0}
- IIIF Image API 3.0 compliance levels: :contentReference[oaicite:1]{index=1}
- Serverless-IIIF docs (source images / implementation hints): :contentReference[oaicite:2]{index=2}

---

## 0. Scope and version strategy

### What you are building
An HTTP service implementing the **IIIF Image API**: a standard URL pattern that returns either:
- derived images (cropped/resized/rotated/reformatted), or
- an image information document (`info.json`) that advertises capabilities to clients. :contentReference[oaicite:3]{index=3}

### Version choice
- **Implement Image API 3.0** first (modern baseline). :contentReference[oaicite:4]{index=4}
- Optional for compatibility: **Image API 2.1** (Serverless-IIIF supports both 2.1 and 3.0). :contentReference[oaicite:5]{index=5}

**Production recommendation:** Support **3.0 Level 1** at minimum (works with most viewers), and consider **Level 2** if you want “full-feature expectations” (percent region, more size options, PNG, 90° rotations). :contentReference[oaicite:6]{index=6}

---

## 1. Required endpoints and URI templates (Image API 3.0)

### 1.1 Image Information Request (required)
**MUST** implement:

`{scheme}://{server}{/prefix}/{identifier}/info.json` :contentReference[oaicite:7]{index=7}

Example:
`https://example.org/image-service/abcd1234/info.json` :contentReference[oaicite:8]{index=8}

### 1.2 Image Request (required)
**MUST** implement the canonical 5-parameter image request:

`{scheme}://{server}{/prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}` :contentReference[oaicite:9]{index=9}

The parameters are always in this order:
`region → size → rotation → quality → format`. :contentReference[oaicite:10]{index=10}

### 1.3 Base URI redirect behavior (required for Level 1+)
**SHOULD / REQUIRED for Level 1+**: dereferencing the image service base URI should redirect to the info document (often via 303). :contentReference[oaicite:11]{index=11}

---

## 2. `info.json` requirements (Image API 3.0)

### 2.1 Minimum required fields (MUST)
Your `info.json` must include (at least):
- `profile` (must be one of `level0`, `level1`, `level2`) :contentReference[oaicite:12]{index=12}
- `width` (integer pixel width of full image) :contentReference[oaicite:13]{index=13}
- `height` (integer pixel height of full image) :contentReference[oaicite:14]{index=14}
- plus the service identity fields defined by the spec (e.g., service `id`, service `type`, and protocol). :contentReference[oaicite:15]{index=15}

**Implementation note:** Your `profile` claim must match the highest level you fully support; do not over-claim. :contentReference[oaicite:16]{index=16}

### 2.2 Advertising supported derivatives (MUST if you advertise them)
If you include advertised capabilities (e.g., tiles, sizes, supported formats/qualities), then:
- You **must** actually serve requests consistent with what you advertise.
- You **should** reject unsupported requests with correct errors (see §6).

(These behaviors are implied by the compliance framework: servers may support only subsets if advertised properly.) :contentReference[oaicite:17]{index=17}

---

## 3. Image request parameters: required semantics

All requests parse:
`/{identifier}/{region}/{size}/{rotation}/{quality}.{format}` :contentReference[oaicite:18]{index=18}

### 3.1 Region (`{region}`)
- Level 0 **MUST** support: `full` :contentReference[oaicite:19]{index=19}
- Level 1 **MUST** additionally support: pixel region `x,y,w,h` and `square` :contentReference[oaicite:20]{index=20}
- Level 2 **MUST** additionally support: `pct:x,y,w,h` :contentReference[oaicite:21]{index=21}

### 3.2 Size (`{size}`)
- Level 0 **MUST** support: `max` :contentReference[oaicite:22]{index=22}
- Level 1 **MUST** additionally support: `w,` and `,h` :contentReference[oaicite:23]{index=23}
- Level 2 **MUST** additionally support: `pct:n`, `w,h`, and `!w,h` :contentReference[oaicite:24]{index=24}

### 3.3 Rotation (`{rotation}`)
- Level 0/1 **MUST** support: `0` :contentReference[oaicite:25]{index=25}
- Level 2 **MUST** additionally support: `90`, `180`, `270` :contentReference[oaicite:26]{index=26}
- Arbitrary rotation is optional (do not claim unless you implement).

### 3.4 Quality (`{quality}`)
- Level 0 **MUST** support: `default` :contentReference[oaicite:27]{index=27}
- Additional qualities are optional; if supported, they must be discoverable via `info.json` and validated.

### 3.5 Format (`{format}`)
- Level 0 **MUST** support: `jpg` :contentReference[oaicite:28]{index=28}
- Level 2 **MUST** additionally support: `png` :contentReference[oaicite:29]{index=29}

---

## 4. Compliance levels: what you may claim

IIIF defines three compliance levels:
- **Level 0**: minimum to be compliant
- **Level 1**: recommended baseline for interoperability
- **Level 2**: highest standard set of parameters/features :contentReference[oaicite:30]{index=30}

### 4.1 Level 0 (minimum viable)
**MUST**:
- `region=full`
- `size=max`
- `rotation=0`
- `quality=default`
- `format=jpg` :contentReference[oaicite:31]{index=31}

### 4.2 Level 1 (recommended)
**MUST** include Level 0 plus:
- region by pixels (`x,y,w,h`) and `square`
- size by width only (`w,`) and height only (`,h`)
- plus additional HTTP features (see §5) :contentReference[oaicite:32]{index=32}

### 4.3 Level 2 (full-feature common expectation)
**MUST** include Level 1 plus:
- region by percent (`pct:x,y,w,h`)
- additional size forms (`pct:n`, `w,h`, `!w,h`)
- rotations at 90° increments (`90/180/270`)
- `png` format :contentReference[oaicite:33]{index=33}

---

## 5. HTTP / production requirements (beyond pure parameter parsing)

### 5.1 Required methods
- **MUST** support `GET` for images and `info.json`. :contentReference[oaicite:34]{index=34}

### 5.2 CORS (required for Level 1+, strongly recommended for production)
- **REQUIRED for Level 1+** to enable browser-based viewers.
- **Production MUST**: CORS headers for `info.json` and image responses, and handle preflight if needed. :contentReference[oaicite:35]{index=35}

### 5.3 Redirect from base service URI (required for Level 1+)
- **REQUIRED for Level 1+**: base URI redirect behavior to `info.json` (commonly 303). :contentReference[oaicite:36]{index=36}

### 5.4 Content negotiation / JSON(-LD)
- The spec defines JSON(-LD) expectations for `info.json` responses.
- **Production SHOULD**: return appropriate content types and be tolerant of clients that accept plain JSON. :contentReference[oaicite:37]{index=37}

---

## 6. Error handling (implementation-critical)

### 6.1 Invalid requests
**MUST** return an error (typically **400 Bad Request**) when:
- a parameter syntax is invalid
- a requested feature is not supported but was requested (e.g., unsupported quality/format/rotation/size pattern)

(Implement strict parsing and clear error responses; do not silently “fix” invalid inputs.)

### 6.2 Unsupported-but-valid patterns at your claimed level
If you claim Level 1/2, you must support all required patterns for that level (or you must lower your `profile` claim). :contentReference[oaicite:38]{index=38}

---

## 7. Identifier rules (critical for infra-agnostic storage resolvers)

IIIF identifiers appear in the URL path segment. Therefore:
- Any special characters must be URI-encoded.
- In particular, if your logical identifier contains `/`, it must be percent-encoded as `%2F` to avoid being treated as a path separator.

Serverless-IIIF explicitly warns about this when mapping object keys to identifiers. :contentReference[oaicite:39]{index=39}

**Production MUST**:
- define a stable mapping: `{identifier} ↔ source object key / asset id`
- ensure encoding/decoding is consistent across AWS/GCP/OCI gateways/CDNs.

---

## 8. Practical “serverless” implementation notes (portable across AWS/GCP/OCI)

### 8.1 Image processing engine
Serverless-IIIF uses a processor built around **libvips-supported formats**; it notes good results from **tiled, multi-resolution TIFFs** and can also handle formats libvips supports (e.g., JP2). :contentReference[oaicite:40]{index=40}

**Production SHOULD**:
- choose an image engine with fast region/resize operations (libvips is a common choice)
- pre-tile / precompute pyramids for large images if you want predictable latency.

### 8.2 “Pipeline vs service wrapper”
Samvera’s approach separates:
- an image processing module (pipeline) and
- a thin serverless wrapper that maps IIIF URLs to reads/writes. :contentReference[oaicite:41]{index=41}

**Production SHOULD** (for infra independence):
- keep the core IIIF parsing + image ops as a portable library
- implement per-cloud adapters for:
  - object storage read (S3/GCS/OCI Object Storage)
  - cache (CDN or object-store cache)
  - auth/signing (optional)
  - logging/metrics.

---

## 9. Implementation checklist (what to build)

### 9.1 MUST (to claim **Image API 3.0 Level 0**)
1. **Routing**
   - `GET /{identifier}/info.json` :contentReference[oaicite:42]{index=42}
   - `GET /{identifier}/{region}/{size}/{rotation}/{quality}.{format}` :contentReference[oaicite:43]{index=43}

2. **info.json generation**
   - include required properties including `profile` + `width` + `height` :contentReference[oaicite:44]{index=44}
   - set `profile` to `level0` and do not claim higher until implemented :contentReference[oaicite:45]{index=45}

3. **Parameter support (Level 0)**
   - region: `full`
   - size: `max`
   - rotation: `0`
   - quality: `default`
   - format: `jpg` :contentReference[oaicite:46]{index=46}

4. **Identifier encoding**
   - implement strict URI encoding/decoding; encode embedded slashes as `%2F` :contentReference[oaicite:47]{index=47}

5. **Errors**
   - reject invalid parameter values/patterns with 400.

### 9.2 REQUIRED for production interoperability (recommend **Level 1**)
- Implement Level 1 region + size patterns (pixel region, square, `w,` and `,h`). :contentReference[oaicite:48]{index=48}
- Enable CORS and base-URI redirect behaviors required by Level 1. :contentReference[oaicite:49]{index=49}

### 9.3 Optional but commonly expected (recommend **Level 2**)
- Implement `pct:` region and additional size patterns (`pct:n`, `w,h`, `!w,h`). :contentReference[oaicite:50]{index=50}
- Support 90° rotations and PNG output. :contentReference[oaicite:51]{index=51}

---

## 10. Recommended “claims” by maturity

### Minimal release (works for basic use)
- Claim: `profile=level0`
- Ensure your `info.json` advertises only what you serve. :contentReference[oaicite:52]{index=52}

### Production baseline (most viewers)
- Claim: `profile=level1`
- Includes CORS + redirect requirements. :contentReference[oaicite:53]{index=53}

### Full-feature service
- Claim: `profile=level2`
- Adds percent region, more size syntaxes, PNG, 90° rotations. :contentReference[oaicite:54]{index=54}

---

## Appendix A — Notes on “Serverless-IIIF” as a reference implementation

- It describes itself as IIIF Image API **2.1 & 3.0 compliant** and packaged as an AWS serverless application. :contentReference[oaicite:55]{index=55}
- It notes the processor can use formats supported by **libvips** and recommends tiled, multi-resolution TIFFs for best results. :contentReference[oaicite:56]{index=56}

Use it as a behavioral reference, but keep your architecture cloud-agnostic by isolating:
- IIIF URL parsing + `info.json` generation (portable core)
- object store resolver + cache + deployment (cloud adapters)
