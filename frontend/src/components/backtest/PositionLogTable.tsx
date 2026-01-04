import React, { useState, useMemo } from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Download } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Trade {
    trade_id: string;
    symbol: string;
    side: 'BUY' | 'SELL';
    entry_time: string;
    entry_price: number;
    exit_time: string;
    exit_price: number;
    quantity: number;
    pnl: number;
    pnl_percent: number;
    status: string;
}

interface PositionLogTableProps {
    trades: Trade[];
}

export const PositionLogTable = React.memo(({ trades }: PositionLogTableProps) => {
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
    const [page, setPage] = useState(1);
    const pageSize = 20;

    // Sorting Logic
    const sortedTrades = useMemo(() => {
        if (!sortColumn) return trades;

        return [...trades].sort((a, b) => {
            let aValue: any;
            let bValue: any;

            switch (sortColumn) {
                case 'side': aValue = a.side; bValue = b.side; break;
                case 'entry_time': aValue = new Date(a.entry_time).getTime(); bValue = new Date(b.entry_time).getTime(); break;
                case 'entry_price': aValue = a.entry_price; bValue = b.entry_price; break;
                case 'quantity': aValue = a.quantity; bValue = b.quantity; break;
                case 'exit_price': aValue = a.exit_price || 0; bValue = b.exit_price || 0; break;
                case 'pnl': aValue = a.pnl; bValue = b.pnl; break;
                case 'symbol': aValue = a.symbol; bValue = b.symbol; break;
                default: return 0;
            }

            if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
            if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }, [trades, sortColumn, sortDirection]);

    // Pagination Logic
    const totalPages = Math.ceil(sortedTrades.length / pageSize);
    const paginatedTrades = useMemo(() => {
        const start = (page - 1) * pageSize;
        return sortedTrades.slice(start, start + pageSize);
    }, [sortedTrades, page, pageSize]);

    const handleSort = (column: string) => {
        if (sortColumn === column) {
            setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortColumn(column);
            setSortDirection('asc');
        }
        setPage(1); // Reset page on sort
    };

    const exportCsv = () => {
        // Simple CSV Export logic (Client side)
        const headers = ['Entry Time', 'Symbol', 'Side', 'Entry Price', 'Exit Time', 'Exit Price', 'Duration', 'Size', 'PnL'];
        const rows = trades.map(t => {
            const durationMs = new Date(t.exit_time).getTime() - new Date(t.entry_time).getTime();
            const durationMinutes = Math.floor(durationMs / 60000); // Simple minutes
            // Better formatting for duration
            const hours = Math.floor(durationMinutes / 60);
            const minutes = durationMinutes % 60;
            const durationStr = `${hours > 0 ? `${hours}h ` : ''}${minutes}m`;

            return [
                t.entry_time, t.symbol, t.side, t.entry_price, t.exit_time, t.exit_price, durationStr, t.quantity, t.pnl
            ]
        });
        const csvContent = "data:text/csv;charset=utf-8," +
            [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "position_log.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    if (trades.length === 0) {
        return (
            <Card>
                <CardHeader><CardTitle>Position Log</CardTitle></CardHeader>
                <CardContent>
                    <div className="text-center py-8 text-muted-foreground">No trades available.</div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>Position Log</CardTitle>
                        <CardDescription>
                            Detailed history of all executed trades ({trades.length} items)
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" onClick={exportCsv}>
                            <Download className="mr-2 h-4 w-4" />
                            Export CSV
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="cursor-pointer" onClick={() => handleSort('entry_time')}>
                                    Entry Time {sortColumn === 'entry_time' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer" onClick={() => handleSort('symbol')}>
                                    Symbol {sortColumn === 'symbol' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer" onClick={() => handleSort('side')}>
                                    Side {sortColumn === 'side' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer text-right" onClick={() => handleSort('entry_price')}>
                                    Entry Price {sortColumn === 'entry_price' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer" onClick={() => handleSort('exit_time')}>
                                    Exit Time {sortColumn === 'exit_time' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer text-right" onClick={() => handleSort('exit_price')}>
                                    Exit Price {sortColumn === 'exit_price' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="text-right">
                                    Duration
                                </TableHead>
                                <TableHead className="cursor-pointer text-right" onClick={() => handleSort('quantity')}>
                                    Size {sortColumn === 'quantity' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer text-right" onClick={() => handleSort('pnl')}>
                                    PnL {sortColumn === 'pnl' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedTrades.map((trade) => (
                                <TableRow key={trade.trade_id}>
                                    <TableCell>{new Date(trade.entry_time).toLocaleString()}</TableCell>
                                    <TableCell className="font-medium">{trade.symbol}</TableCell>
                                    <TableCell>
                                        <Badge variant={trade.side === 'BUY' ? 'default' : 'destructive'}>
                                            {trade.side}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-right">${trade.entry_price.toLocaleString()}</TableCell>
                                    <TableCell>{trade.exit_time ? new Date(trade.exit_time).toLocaleString() : '-'}</TableCell>
                                    <TableCell className="text-right">
                                        {trade.exit_price ? `$${trade.exit_price.toLocaleString()}` : '-'}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        {(() => {
                                            if (!trade.exit_time || !trade.entry_time) return '-';
                                            const diff = new Date(trade.exit_time).getTime() - new Date(trade.entry_time).getTime();
                                            const sec = Math.floor(diff / 1000);
                                            const min = Math.floor(sec / 60);
                                            const hr = Math.floor(min / 60);
                                            const days = Math.floor(hr / 24);

                                            if (days > 0) return `${days}d ${hr % 24}h`;
                                            if (hr > 0) return `${hr}h ${min % 60}m`;
                                            if (min > 0) return `${min}m ${sec % 60}s`;
                                            return `${sec}s`;
                                        })()}
                                    </TableCell>
                                    <TableCell className="text-right">{trade.quantity}</TableCell>
                                    <TableCell className={cn(
                                        "text-right font-medium",
                                        trade.pnl > 0 ? "text-green-600" : trade.pnl < 0 ? "text-red-600" : ""
                                    )}>
                                        {trade.pnl > 0 ? '+' : ''}{trade.pnl.toLocaleString()} ({trade.pnl_percent.toFixed(2)}%)
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
                {/* Pagination Controls */}
                <div className="flex items-center justify-end space-x-2 py-4">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                    >
                        Previous
                    </Button>
                    <div className="text-sm text-gray-500">
                        Page {page} of {Math.max(1, totalPages)}
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page >= totalPages}
                    >
                        Next
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
});

PositionLogTable.displayName = 'PositionLogTable';
