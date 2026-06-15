export function asResults(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.results)) {
    return payload.results;
  }
  return [];
}

export function asPaginated(payload) {
  if (Array.isArray(payload)) {
    return {
      results: payload,
      count: payload.length,
      next: null,
      previous: null,
      isPaginated: false,
    };
  }

  if (payload && Array.isArray(payload.results)) {
    return {
      results: payload.results,
      count: payload.count ?? payload.results.length,
      next: payload.next ?? null,
      previous: payload.previous ?? null,
      isPaginated: true,
    };
  }

  return {
    results: [],
    count: 0,
    next: null,
    previous: null,
    isPaginated: false,
  };
}
