import { useState } from 'react';
import { Check, LoaderCircle, Search } from 'lucide-react';
import { findLocations } from '../api';
import type { Location } from '../types';

interface Props {
  label: string;
  location: Location | null;
  marker: string;
  onChange: (location: Location | null) => void;
}

export default function LocationInput({ label, location, marker, onChange }: Props) {
  const [query, setQuery] = useState(location?.label ?? '');
  const [results, setResults] = useState<Location[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState('');

  async function search() {
    if (query.trim().length < 3) {
      setError('Enter at least 3 characters.');
      return;
    }
    setSearching(true);
    setError('');
    try {
      const response = await findLocations(query.trim());
      setResults(response.results);
      if (!response.results.length)
        setError('No results found. Try a city and state or a full address.');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Search failed.');
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="location-field">
      <label htmlFor={`location-${marker}`}>
        <span className={`location-bullet bullet-${marker}`}>{marker}</span>
        {label}
      </label>
      <div className={`location-input ${location ? 'resolved' : ''}`}>
        <input
          id={`location-${marker}`}
          value={query}
          disabled={searching}
          placeholder="City, state or address"
          autoComplete="off"
          onChange={(event) => {
            setQuery(event.target.value);
            onChange(null);
            setResults([]);
            setError('');
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              void search();
            }
          }}
        />
        <button
          type="button"
          aria-label={`Search ${label.toLowerCase()}`}
          disabled={searching}
          onClick={() => void search()}
        >
          {searching ? (
            <LoaderCircle size={16} className="spin" />
          ) : location ? (
            <Check size={16} />
          ) : (
            <Search size={16} />
          )}
        </button>
      </div>
      {!!results.length && (
        <div className="location-results" role="list" aria-label={`${label} search results`}>
          {results.map((result) => (
            <button
              type="button"
              key={`${result.latitude},${result.longitude}`}
              onClick={() => {
                onChange(result);
                setQuery(result.label);
                setResults([]);
              }}
            >
              <span>{result.label}</span>
              <Check size={14} />
            </button>
          ))}
        </div>
      )}
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
