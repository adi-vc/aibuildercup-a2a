/**
 * composition.tsx — the Remotion composition (vachan-plan.md §29, §47).
 *
 * One <Sequence> per segment of the viewer's *path* (path.ts): holds, and the
 * edge clips between them (§26). Each hold stacks the §47 layers:
 *   L0 plate      — the only generated pixels, identical for every viewer
 *   L1 motion     — depth parallax (WebGL), else Ken Burns, else none (§29 ladder)
 *   L3 text       — locale copy + the resolved binding (price), never baked
 *   L4 UI         — fact badges that open the cited span
 * Nothing here generates: every input arrives as props, so a locale or city
 * swap is a re-render of layers over the same plate. A failing plate or
 * shader drops a rung; the text layer is independent and always renders.
 * Holds begin and end on their hinge frame, so a clip joins them exactly.
 */

import { useCallback, useEffect, useState } from 'react';
import { AbsoluteFill, Html5Video, Img, interpolate, Sequence, useCurrentFrame } from 'remotion';
import type { Beat, Edge, Manifest } from '../types/manifest';
import { bindingTag, type BindingResolution } from './bindings';
import { shownFactIds } from './claims';
import styles from './composition.module.css';
import { DepthParallax } from './DepthParallax';
import { markFirstFrame } from './firstFrame';
import { timeline, type Segment } from './path';
import { kenBurnsScale, TEXT_IN_START, TEXT_SETTLED } from './timeline';
import { renderPlan, type Tier, type ViewerEnv } from './tier';

export interface CompositionProps extends Record<string, unknown> {
  manifest: Manifest;
  locale: string;
  bindings: Record<string, BindingResolution>;
  /** Degradation-ladder inputs (tier.ts). */
  env: { tier: Tier; viewer: ViewerEnv };
  /** What plays, in order: holds and edge clips (path.ts). */
  path: Segment[];
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
        <span className={styles.check} aria-hidden="true">
          <svg viewBox="0 0 16 16" width="14" height="14"><path d="M3 8.5l3.2 3L13 4.5" fill="none" stroke="currentColor" strokeWidth="2.2" /></svg>
        </span>
        Verified
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
  const scale = motion === 'kenburns' ? kenBurnsScale(frame) : 1;
  return (
    <Img
      src={plateSrc}
      className={styles.plate}
      width={1280}
      height={720}
      alt=""
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

      {/* L3: a branch beat's spec sheet — published facts, each with its badge (§18 b_spec_overlay) */}
      {beat.branch_only && (
        <ul className={styles.specPanel} style={{ opacity: textIn }}>
          {beat.fact_ids.map((fid) => (
            <li key={fid}>{manifest.integrity.facts?.[fid]?.text ?? fid}</li>
          ))}
        </ul>
      )}

      {/* L4 */}
      <div className={styles.badgeRow}>
        {shownFactIds(beat, bindings).map((fid) => (
          <FactBadge key={fid} factId={fid} manifest={manifest} />
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ── One edge clip ────────────────────────────────────────────────────────────

/**
 * L0 is the generated clip; the source beat's copy fades over the first
 * quarter so text leaves with the footage. Clips are all-intra (§39.12), so
 * the Player can seek them to any frame in either direction. Below the
 * `low` tier, or under reduced motion, the edge is a cut to the target plate.
 */
function EdgeClip({ edge, frames, manifest, locale, env }: { edge: Edge; frames: number } & CompositionProps) {
  const frame = useCurrentFrame();
  const clip = manifest.vault[edge.clip];
  const from = manifest.beats.find((b) => b.id === edge.from);
  const target = manifest.vault[manifest.beats.find((b) => b.id === edge.to)?.vault_refs[0] ?? ''];
  const clipsAllowed = renderPlan(env.tier, env.viewer, false).clips;
  const fadeOut = interpolate(frame, [0, Math.max(1, frames * 0.25)], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const text = from ? from.text_slots[locale] ?? from.text_slots['en-IN'] ?? '' : '';

  return (
    <AbsoluteFill className={styles.hold} data-edge={edge.id}>
      {clip && clipsAllowed ? (
        <Html5Video src={clip.uri} muted className={styles.plate} />
      ) : target ? (
        <Img src={target.uri} className={styles.plate} width={1280} height={720} alt="" />
      ) : (
        <AbsoluteFill className={styles.platePlaceholder} />
      )}
      {text && clipsAllowed && (
        <div className={styles.textLayer} style={{ opacity: fadeOut }}>
          <p className={styles.beatText} lang={locale}>{text}</p>
        </div>
      )}
    </AbsoluteFill>
  );
}

export function VachanComposition(props: CompositionProps) {
  const beats = new Map(props.manifest.beats.map((b) => [b.id, b]));
  const edges = new Map(props.manifest.edges.map((e) => [e.id, e]));
  return (
    <AbsoluteFill className={styles.stage}>
      {timeline(props.manifest, props.path).map(({ segment, start, frames }, i) => {
        const id = segment.kind === 'hold' ? segment.beatId : segment.edgeId;
        const beat = segment.kind === 'hold' ? beats.get(segment.beatId) : undefined;
        const edge = segment.kind === 'edge' ? edges.get(segment.edgeId) : undefined;
        return (
          <Sequence key={`${i}-${id}`} from={start} durationInFrames={frames} name={id}>
            {beat && <Hold beat={beat} {...props} />}
            {edge && <EdgeClip edge={edge} frames={frames} {...props} />}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
}
