export default function Loading() {
  return (
    <main className="shell loading-shell" aria-busy="true" aria-label="Cargando MatchLab">
      <div className="skeleton skeleton-hero" />
      <div className="skeleton-row">
        <div className="skeleton" />
        <div className="skeleton" />
        <div className="skeleton" />
        <div className="skeleton wide" />
      </div>
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-card" />
      <div className="skeleton skeleton-card" />
    </main>
  );
}
