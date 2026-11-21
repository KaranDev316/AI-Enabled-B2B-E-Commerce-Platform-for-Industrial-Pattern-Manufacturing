/**
 * Re-export kpcLiveSync for seamless backwards compatibility.
 */
export {
  emitKpcSync,
  emitKpcSync as emitCrossTabEvent,
  useKpcLiveSync,
  useKpcLiveSync as useCrossTabSync,
  LiveSyncBadge,
} from './kpcLiveSync';
