/**
 * React hooks for NFT price prediction functionality
 */
import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { 
  predictNFTPrice, 
  getPricePredictionCategories,
  checkPricePredictionHealth,
  type PricePredictionRequest,
  type PricePredictionResponse,
  type CategoriesResponse
} from '@/lib/api';

// Hook for getting available categories
export const usePricePredictionCategories = () => {
  return useQuery({
    queryKey: ['price-prediction', 'categories'],
    queryFn: getPricePredictionCategories,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
};

// Hook for checking price prediction service health
export const usePricePredictionHealth = () => {
  return useQuery({
    queryKey: ['price-prediction', 'health'],
    queryFn: checkPricePredictionHealth,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
};

// Hook for manual price prediction
export const usePricePrediction = () => {
  return useMutation({
    mutationFn: predictNFTPrice,
    onError: (error) => {
      console.error('Price prediction failed:', error);
    },
  });
};

// Hook for real-time price prediction with debouncing
export const useRealtimePricePrediction = (
  title: string,
  description: string,
  category: string,
  enabled: boolean = true,
  debounceMs: number = 1000
) => {
  const [debouncedValues, setDebouncedValues] = useState({
    title: '',
    description: '',
    category: ''
  });
  const [isDebouncing, setIsDebouncing] = useState(false);

  // Debounce the input values
  useEffect(() => {
    setIsDebouncing(true);
    const timer = setTimeout(() => {
      setDebouncedValues({
        title: title.trim(),
        description: description.trim(),
        category
      });
      setIsDebouncing(false);
    }, debounceMs);

    return () => {
      clearTimeout(timer);
      setIsDebouncing(false);
    };
  }, [title, description, category, debounceMs]);

  // Check if we have enough data for prediction
  const hasValidData = 
    debouncedValues.title.length >= 3 &&
    debouncedValues.description.length >= 10 &&
    debouncedValues.category.length > 0;

  // Query for price prediction
  const query = useQuery({
    queryKey: ['price-prediction', 'realtime', debouncedValues],
    queryFn: () => predictNFTPrice(debouncedValues),
    enabled: enabled && hasValidData && !isDebouncing,
    staleTime: 30 * 1000, // 30 seconds
    refetchOnWindowFocus: false,
    retry: 1,
  });

  return {
    ...query,
    isDebouncing,
    hasValidData,
    debouncedValues
  };
};

// Hook for price prediction with validation
export const usePricePredictionWithValidation = () => {
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  
  const validateInput = useCallback((request: PricePredictionRequest): boolean => {
    const errors: string[] = [];
    
    if (!request.title || request.title.trim().length < 3) {
      errors.push('Title must be at least 3 characters long');
    }
    if (request.title && request.title.trim().length > 100) {
      errors.push('Title must be less than 100 characters');
    }
    
    if (!request.description || request.description.trim().length < 10) {
      errors.push('Description must be at least 10 characters long');
    }
    if (request.description && request.description.trim().length > 1000) {
      errors.push('Description must be less than 1000 characters');
    }
    
    if (!request.category) {
      errors.push('Category is required');
    }
    
    setValidationErrors(errors);
    return errors.length === 0;
  }, []);

  const mutation = useMutation({
    mutationFn: async (request: PricePredictionRequest) => {
      if (!validateInput(request)) {
        throw new Error('Validation failed');
      }
      return predictNFTPrice(request);
    },
    onError: (error) => {
      console.error('Price prediction failed:', error);
    },
  });

  return {
    ...mutation,
    validationErrors,
    validateInput,
    clearValidationErrors: () => setValidationErrors([])
  };
};

// Hook for price comparison (multiple predictions)
export const usePriceComparison = () => {
  const [predictions, setPredictions] = useState<PricePredictionResponse[]>([]);
  const [isComparing, setIsComparing] = useState(false);

  const addPrediction = useCallback(async (request: PricePredictionRequest) => {
    setIsComparing(true);
    try {
      const result = await predictNFTPrice(request);
      setPredictions(prev => [...prev, result]);
      return result;
    } catch (error) {
      console.error('Failed to add prediction:', error);
      throw error;
    } finally {
      setIsComparing(false);
    }
  }, []);

  const clearPredictions = useCallback(() => {
    setPredictions([]);
  }, []);

  const removePrediction = useCallback((index: number) => {
    setPredictions(prev => prev.filter((_, i) => i !== index));
  }, []);

  const getAveragePrice = useCallback(() => {
    if (predictions.length === 0) return 0;
    const validPredictions = predictions.filter(p => p.success && p.predicted_price);
    if (validPredictions.length === 0) return 0;
    
    const sum = validPredictions.reduce((acc, p) => acc + (p.predicted_price || 0), 0);
    return sum / validPredictions.length;
  }, [predictions]);

  const getAverageConfidence = useCallback(() => {
    if (predictions.length === 0) return 0;
    const sum = predictions.reduce((acc, p) => acc + p.confidence_score, 0);
    return sum / predictions.length;
  }, [predictions]);

  return {
    predictions,
    isComparing,
    addPrediction,
    clearPredictions,
    removePrediction,
    getAveragePrice,
    getAverageConfidence
  };
};

// Utility function to format price with currency
export const formatPredictedPrice = (price: number | undefined, currency: string = 'SUI'): string => {
  if (price === undefined || price === null) return 'N/A';
  return `${price.toFixed(2)} ${currency}`;
};

// Utility function to format confidence score
export const formatConfidenceScore = (score: number): string => {
  return `${(score * 100).toFixed(1)}%`;
};

// Utility function to get confidence level description
export const getConfidenceLevel = (score: number): { level: string; color: string } => {
  if (score >= 0.8) return { level: 'High', color: 'text-green-600' };
  if (score >= 0.6) return { level: 'Medium', color: 'text-yellow-600' };
  return { level: 'Low', color: 'text-red-600' };
};
