/**
 * composition.tsx — the Remotion composition (vachan-plan.md §29, §47).
 *
 * One <Sequence> per hold beat. Each hold stacks the §47 layers:
 *   L0 plate      — the only generated pixels, identical for every viewer
 *   L1 motion     — depth parallax (WebGL), else Ken Burns, else none (§29 ladder)
 *   L3 text       — locale copy + the resolved binding (price), never baked
 *   L4 UI         — fact badges that open the cited span
 * Nothing here generates: every input arrives as props, so a locale or city
 * swap is a re-render of layers over the same plate. A failing plate or
 * shader drops a rung; the text layer is independent and always renders.
 */

import { useCallback, useEffect, useState } from 'react';
import { AbsoluteFill, Img, interpolate, Sequence, useCurrentFrame } from 'remotion';
import type { Beat, Manifest } from '../types/manifest';
import { bindingTag, type BindingResolution } from './bindings';
import styles from './composition.module.css';
import { DepthParallax } from './DepthParallax';
import { markFirstFrame } from './firstFrame';
import { HOLD_FRAMES, TEXT_IN_START, TEXT_SETTLED } from './timeline';
import { renderPlan, type Tier, type ViewerEnv } from './tier';

export interface CompositionProps extends Record<string, unknown> {
  manifest: Manifest;
  locale: string;
  bindings: Record<string, BindingResolution>;
  /** Degradation-ladder inputs (tier.ts). */
  env: { tier: Tier; viewer: ViewerEnv };
}

// ── L4: fact badge ───────────────────────────────────────────────────────────

function FactBadge({ factId, manifest }: { factId: string; manifest: Manifest }) {
  const [open, setOpen] = useState(false);
  const spanId = manifest.integrity.fact_index[factId] ?? '—';
  const published = manifest.integrity.facts?.[factId];
  return (
    <div className={styles.factBadge}>
      <button
        className={styles.badgeButton}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={`View source for ${factId}`}
      >
        ✓ verified
      </button>
      {open && (
        <div className={styles.badgePanel} role="tooltip">
          {published && <p className={styles.badgeQuote}>“{published.quote}”</p>}
          <p><strong>fact:</strong> {factId}</p>
          <p><strong>span:</strong> {spanId}</p>
          <p><strong>origin:</strong> {published?.origin ?? 'canon'}</p>
        </div>
      )}
    </div>
  );
}

// ── L3: a resolved binding ───────────────────────────────────────────────────

function BindingLine({ resolution, locale }: { resolution: BindingResolution; locale: string }) {
  const tag = bindingTag(resolution, locale);
  return (
    <p className={styles.bindingLine} data-rung={resolution.rung}>
      <span className={resolution.rung === 4 ? styles.neutral : styles.bindingValue}>{resolution.display}</span>
      {tag && <span className={styles.bindingTag}>{tag}</span>}
    </p>
  );
}

// ── L4: which facts get a badge ──────────────────────────────────────────────

/** Badges for what is actually claimed on screen. A bound beat cites one fact
 *  per city; only the fallback fact actually shown (rung 3) gets a badge. */
function shownFactIds(beat: Beat, bindings: Record<string, BindingResolution>): string[] {
  if (beat.bindings.length === 0) return beat.fact_ids;
  return beat.bindings
    .map((key) => bindings[key]?.source)
    .flatMap((src) => (src?.kind === 'fact' ? [src.fact_id] : []));
}

// ── L0 + L1 ──────────────────────────────────────────────────────────────────

function PlateLayer({ beat, manifest, env }: Pick<CompositionProps, 'manifest' | 'env'> & { beat: Beat }) {
  const frame = useCurrentFrame();
  const asset = manifest.vault[beat.vault_refs[0] ?? ''];
  const plan = renderPlan(env.tier, env.viewer, !!asset?.depth_uri);
  const [failed, setFailed] = useState<'none' | 'parallax' | 'plate'>('none');
  const plateSrc = asset ? (plan.plate === 'poster' ? asset.poster_uri || asset.uri : asset.uri) : '';
  const motion = plan.motion === 'parallax' && failed === 'parallax' ? 'kenburns' : plan.motion;
  const showFallback = !asset || failed === 'plate';

  const onParallaxReady = useCallback(() => markFirstFrame(beat.id, 'parallax'), [beat.id]);
  const onParallaxFallback = useCallback(() => setFailed('parallax'), []);
  useEffect(() => {
    if (showFallback) markFirstFrame(beat.id, 'fallback');
  }, [showFallback, beat.id]);

  if (showFallback) {
    return <AbsoluteFill className={styles.platePlaceholder} />;
  }
  if (motion === 'parallax') {
    return (
      <DepthParallax
        plateSrc={plateSrc}
        depthSrc={asset.depth_uri!}
        className={styles.plate}
        onReady={onParallaxReady}
        onFallback={onParallaxFallback}
      />
    );
  }
  const scale = motion === 'kenburns' ? interpolate(frame, [0, HOLD_FRAMES], [1, 1.06]) : 1;
  return (
    <Img
      src={plateSrc}
      className={styles.plate}
      style={{ transform: `scale(${scale})` }}
      maxRetries={1}
      onLoad={() => markFirstFrame(beat.id, 'plate')}
      onError={() => setFailed('plate')}
    />
  );
}

// ── One hold ─────────────────────────────────────────────────────────────────

function Hold({ beat, manifest, locale, bindings, env }: { beat: Beat } & CompositionProps) {
  const frame = useCurrentFrame();
  const textIn = interpolate(frame, [TEXT_IN_START, TEXT_SETTLED], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const text = beat.text_slots[locale] ?? beat.text_slots['en-IN'] ?? '';

  return (
    <AbsoluteFill className={styles.hold} data-beat={beat.id}>
      {/* L0 + L1 */}
      <PlateLayer beat={beat} manifest={manifest} env={env} />

      {/* L3 */}
      <div className={styles.textLayer} style={{ opacity: textIn }}>
        <p className={styles.beatText} lang={locale}>{text}</p>
        {beat.bindings.map((key) =>
          bindings[key] ? <BindingLine key={key} resolution={bindings[key]} locale={locale} /> : null,
        )}
      </div>

      {/* L4 */}
      <div className={styles.badgeRow}>
        {shownFactIds(beat, bindings).map((fid) => (
          <FactBadge key={fid} factId={fid} manifest={manifest} />
        ))}
      </div>
    </AbsoluteFill>
  );
}

export function VachanComposition(props: CompositionProps) {
  return (
    <AbsoluteFill className={styles.stage}>
      {props.manifest.beats.map((beat, i) => (
        <Sequence key={beat.id} from={i * HOLD_FRAMES} durationInFrames={HOLD_FRAMES} name={beat.id}>
          <Hold beat={beat} {...props} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
