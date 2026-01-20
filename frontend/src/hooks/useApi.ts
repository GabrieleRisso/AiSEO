import { useState, useEffect, useCallback } from 'react';
import {
  fetchBrands,
  fetchPrompts,
  fetchPromptDetail,
  fetchSources,
  fetchMetrics,
  fetchVisibilityData,
  fetchSourcesAnalytics,
  fetchSuggestions,
  fetchBrandsDetails,
  type BrandResponse,
  type PromptResponse,
  type PromptDetailResponse,
  type SourceResponse,
  type DashboardMetricsResponse,
  type DailyVisibilityResponse,
  type SourcesAnalyticsResponse,
  type SuggestionsDataResponse,
  type BrandsListResponse,
} from '../api/client';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

export function useBrands() {
  const [state, setState] = useState<UseApiState<BrandResponse[]>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetchBrands()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, []);

  return state;
}

export function usePrompts() {
  const [state, setState] = useState<UseApiState<PromptResponse[]>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetchPrompts()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, []);

  return state;
}

export function usePromptDetail(promptId: number | null) {
  const [state, setState] = useState<UseApiState<PromptDetailResponse>>({
    data: null,
    loading: false,
    error: null,
  });

  useEffect(() => {
    if (promptId === null) {
      setState({ data: null, loading: false, error: null });
      return;
    }

    setState({ data: null, loading: true, error: null });
    fetchPromptDetail(promptId)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, [promptId]);

  return state;
}

export function useSources() {
  const [state, setState] = useState<UseApiState<SourceResponse[]>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetchSources()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, []);

  return state;
}

export function useMetrics() {
  const [state, setState] = useState<UseApiState<DashboardMetricsResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetchMetrics()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, []);

  return state;
}

export function useVisibilityData() {
  const [state, setState] = useState<UseApiState<DailyVisibilityResponse[]>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetchVisibilityData()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, []);

  return state;
}

export function useSourcesAnalytics() {
  const [state, setState] = useState<UseApiState<SourcesAnalyticsResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetchSourcesAnalytics()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, []);

  return state;
}

export function useSuggestions() {
  const [state, setState] = useState<UseApiState<SuggestionsDataResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetchSuggestions()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, []);

  return state;
}

export function useBrandsDetails() {
  const [state, setState] = useState<UseApiState<BrandsListResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  const refetch = useCallback(() => {
    setState(prev => ({ ...prev, loading: true }));
    fetchBrandsDetails()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { ...state, refetch };
}
