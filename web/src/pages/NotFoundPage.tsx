import { Link } from 'react-router';

export function NotFoundPage() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-3xl font-bold">Page not found</h1>
      <Link to="/" className="mt-4 inline-block text-lg font-semibold text-sky-800 underline">
        Back to the library
      </Link>
    </div>
  );
}
