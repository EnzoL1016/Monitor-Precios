export interface PriceHistory {
  captured_price: number;
  timestamp: string;
}

export interface Product {
  id: number;
  name: string;
  url: string;
  target_price: string;
  current_price: number | null;
  is_available: boolean;
  history: PriceHistory[];
}