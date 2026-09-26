export default function RawJson({ data }: { data: unknown }) {
  return (
    <details className="raw">
      <summary>Raw response</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}
