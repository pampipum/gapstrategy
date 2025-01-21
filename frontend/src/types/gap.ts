export interface Gap {
    symbol: string;
    companyName: string;
    sector?: string;
    date: string;
    gap_type: 'up' | 'down';
    gap_size: number;
    price?: number;
    volume?: number;
    avg_volume?: number;
    relative_volume?: number;
    market_cap?: number;
    prev_high?: number;
    prev_low?: number;
    current_open?: number;
}

export interface ChartDataPoint {
    date: string;
    count: number;
    up: number;
    down: number;
}