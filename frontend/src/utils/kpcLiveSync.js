import React, { useEffect, useRef, useState, useCallback } from 'react';

const CHANNEL_NAME = 'kpc_b2b_live_sync';
const FALLBACK_KEY = 'kpc_b2b_live_sync_fallback';

// Generate a unique per-tab ID so a tab never triggers a redundant re-fetch from its own action
const TAB_INSTANCE_ID = typeof window !== 'undefined'
  ? (window.__kpcTabInstanceId || (window.__kpcTabInstanceId = 'tab_' + Math.random().toString(36).substring(2, 10)))
  : 'srv';

let liveChannel = null;
if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
  try {
    liveChannel = new BroadcastChannel(CHANNEL_NAME);
  } catch (err) {
    console.warn('[kpcLiveSync] BroadcastChannel initialization failed, falling back to storage:', err);
    liveChannel = null;
  }
}

/**
 * Emit a real-time event to all other open tabs in the same browser window.
 * 
 * @param {string} eventType - E.g. 'RFQ_CREATED', 'QUOTATION_DECIDED', 'INQUIRY_SUBMITTED', 'CATALOGUE_UPDATED', 'ORDER_UPDATED'
 * @param {object} [meta={}] - Additional event payload / metadata
 */
export function emitKpcSync(eventType, meta = {}) {
  const syncPacket = {
    eventType,
    meta,
    senderTabId: TAB_INSTANCE_ID,
    timestamp: Date.now(),
  };

  // 1. Native BroadcastChannel for zero-latency multi-tab sync
  if (liveChannel) {
    try {
      liveChannel.postMessage(syncPacket);
    } catch (e) {
      console.warn('[kpcLiveSync] BroadcastChannel postMessage error:', e);
    }
  }

  // 2. Storage event fallback
  try {
    localStorage.setItem(FALLBACK_KEY, JSON.stringify(syncPacket));
  } catch (_) {
    // Storage quota or sandboxed iframe safety
  }

  // 3. Custom event for local tab subscribers
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('kpc:sync', { detail: syncPacket }));
  }
}

// Backward-compatible alias
export const emitCrossTabEvent = emitKpcSync;

/**
 * React hook that connects a component to real-time cross-tab state updates.
 * Fires `onRefresh` immediately when an event arrives from another tab, when the tab gains focus/visibility,
 * or on visibility-aware interval polling as a fallback.
 * 
 * @param {Function} onRefresh - Callback invoked with syncPacket to silently re-fetch fresh data
 * @param {number} [pollMs=4000] - Interval in ms for smart active-tab background polling
 * @returns {object} { lastSync, isLiveSynced, dismissLiveNotice }
 */
export function useKpcLiveSync(onRefresh, pollMs = 4000) {
  const [lastSync, setLastSync] = useState(null);
  const [isLiveSynced, setIsLiveSynced] = useState(false);
  const onRefreshRef = useRef(onRefresh);
  const badgeTimerRef = useRef(null);

  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  const handleSyncTrigger = useCallback((syncPacket, showBadge = true) => {
    setLastSync(syncPacket || { eventType: 'POLL', timestamp: Date.now() });

    if (showBadge) {
      setIsLiveSynced(true);
      if (badgeTimerRef.current) clearTimeout(badgeTimerRef.current);
      badgeTimerRef.current = setTimeout(() => {
        setIsLiveSynced(false);
      }, 3500);
    }

    if (typeof onRefreshRef.current === 'function') {
      try {
        onRefreshRef.current(syncPacket);
      } catch (err) {
        console.error('[kpcLiveSync] onRefresh callback error:', err);
      }
    }
  }, []);

  useEffect(() => {
    // 1. BroadcastChannel message listener
    const onBroadcastMessage = (event) => {
      if (event.data && event.data.senderTabId !== TAB_INSTANCE_ID) {
        handleSyncTrigger(event.data, true);
      }
    };

    if (liveChannel) {
      liveChannel.addEventListener('message', onBroadcastMessage);
    }

    // 2. Storage fallback listener (fires exclusively in OTHER tabs)
    const onStorageChange = (e) => {
      if (e.key === FALLBACK_KEY && e.newValue) {
        try {
          const packet = JSON.parse(e.newValue);
          if (packet && packet.senderTabId !== TAB_INSTANCE_ID) {
            handleSyncTrigger(packet, true);
          }
        } catch (_) {}
      }
    };
    window.addEventListener('storage', onStorageChange);

    // 3. Tab visibility / focus re-fetch (silent background refresh when returning to tab)
    const onVisibilityOrFocus = () => {
      if (document.visibilityState === 'visible') {
        handleSyncTrigger({ eventType: 'TAB_ACTIVE', timestamp: Date.now() }, false);
      }
    };
    document.addEventListener('visibilitychange', onVisibilityOrFocus);
    window.addEventListener('focus', onVisibilityOrFocus);

    // 4. Lightweight active-tab background polling fallback
    let pollTimer = null;
    if (pollMs && pollMs > 0) {
      pollTimer = setInterval(() => {
        if (document.visibilityState === 'visible') {
          handleSyncTrigger({ eventType: 'BACKGROUND_POLL', timestamp: Date.now() }, false);
        }
      }, pollMs);
    }

    return () => {
      if (liveChannel) {
        liveChannel.removeEventListener('message', onBroadcastMessage);
      }
      window.removeEventListener('storage', onStorageChange);
      document.removeEventListener('visibilitychange', onVisibilityOrFocus);
      window.removeEventListener('focus', onVisibilityOrFocus);
      if (pollTimer) clearInterval(pollTimer);
      if (badgeTimerRef.current) clearTimeout(badgeTimerRef.current);
    };
  }, [handleSyncTrigger, pollMs]);

  return {
    lastSync,
    isLiveSynced,
    isLiveUpdated: isLiveSynced,
    dismissLiveNotice: () => setIsLiveSynced(false),
  };
}

// Backward-compatible alias
export const useCrossTabSync = useKpcLiveSync;

/**
 * Non-intrusive floating toast/badge showing real-time synchronization.
 */
export function LiveSyncBadge({ visible, message = '⚡ Live Synced' }) {
  if (!visible) return null;
  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        backgroundColor: '#0f172a',
        color: '#f8fafc',
        padding: '8px 16px',
        borderRadius: '20px',
        fontSize: '13px',
        fontWeight: '600',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.35)',
        border: '1px solid #38bdf8',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        zIndex: 99999,
        pointerEvents: 'none',
        transition: 'opacity 0.25s ease-in-out',
      }}
      role="status"
      aria-live="polite"
    >
      <span style={{ color: '#38bdf8', fontSize: '15px' }}>⚡</span>
      <span>{message}</span>
    </div>
  );
}
