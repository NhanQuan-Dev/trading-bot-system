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
import { Download, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

interface Trade {
    trade_id: string;
    symbol: string;
    side: string;
    entry_time: string;
    entry_price: number;
    exit_time: string;
    exit_price: number;
    quantity: number;
    pnl: number;
    pnl_percent: number;
    status: string;
    entry_reason?: Record<string, any>;
    exit_reason?: Record<string, any>;
}

interface PositionLogTableProps {
    trades: Trade[];
}

export const PositionLogTable = React.memo(({ trades }: PositionLogTableProps) => {
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
    const [page, setPage] = useState(1);
    const pageSize = 20;

    // Entry Reason Dialog State
    const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);

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
        <Card className="border-border bg-card">
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Position Log</CardTitle>
                    <CardDescription>Detailed history of all executed trades ({trades.length} items)</CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={exportCsv} className="gap-2">
                    <Download className="h-4 w-4" />
                    Export CSV
                </Button>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border border-border">
                    <Table>
                        <TableHeader>
                            <TableRow className="border-border hover:bg-transparent">
                                <TableHead className="cursor-pointer hover:text-primary" onClick={() => handleSort('entry_time')}>
                                    Entry Time {sortColumn === 'entry_time' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary" onClick={() => handleSort('symbol')}>
                                    Symbol {sortColumn === 'symbol' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-center" onClick={() => handleSort('side')}>
                                    Side {sortColumn === 'side' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('entry_price')}>
                                    Entry Price {sortColumn === 'entry_price' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="text-right">Exit Time</TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('exit_price')}>
                                    Exit Price {sortColumn === 'exit_price' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="text-right">Duration</TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('quantity')}>
                                    Size {sortColumn === 'quantity' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="cursor-pointer hover:text-primary text-right" onClick={() => handleSort('pnl')}>
                                    PnL {sortColumn === 'pnl' && (sortDirection === 'asc' ? '↑' : '↓')}
                                </TableHead>
                                <TableHead className="text-center w-[80px]">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {paginatedTrades.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">
                                        No trades recorded yet.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                paginatedTrades.map((trade) => {
                                    // Calculate duration for display
                                    // Parse ISO dates
                                    const entryDate = new Date(trade.entry_time);
                                    const exitDate = new Date(trade.exit_time);
                                    const durationMs = exitDate.getTime() - entryDate.getTime();
                                    const durationSec = Math.floor(durationMs / 1000);

                                    let durationStr = `${durationSec}s`;
                                    if (durationSec > 60) {
                                        const mins = Math.floor(durationSec / 60);
                                        durationStr = `${mins}m ${durationSec % 60}s`;
                                        if (mins > 60) {
                                            const hours = Math.floor(mins / 60);
                                            durationStr = `${hours}h ${mins % 60}m`;
                                        }
                                    }

                                    const isWin = trade.pnl > 0;

                                    return (
                                        <TableRow key={trade.trade_id || Math.random()} className="border-border hover:bg-muted/50">
                                            <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                                                {entryDate.toLocaleString()}
                                            </TableCell>
                                            <TableCell className="font-medium">{trade.symbol}</TableCell>
                                            <TableCell className="text-center">
                                                <Badge
                                                    variant="secondary"
                                                    className={cn(
                                                        "font-mono text-xs uppercase w-16 justify-center",
                                                        (trade.side?.toLowerCase() === 'long' || trade.side?.toLowerCase() === 'buy') ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"
                                                    )}
                                                >
                                                    {(trade.side?.toLowerCase()) === 'long' || trade.side?.toLowerCase() === 'buy' ? 'LONG' : 'SHORT'}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-right font-mono text-xs">
                                                ${trade.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                                            </TableCell>
                                            <TableCell className="text-right font-mono text-xs text-muted-foreground whitespace-nowrap">
                                                {exitDate.toLocaleString()}
                                            </TableCell>
                                            <TableCell className="text-right font-mono text-xs">
                                                ${trade.exit_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                                            </TableCell>
                                            <TableCell className="text-right font-mono text-xs text-muted-foreground">
                                                {durationStr}
                                            </TableCell>
                                            <TableCell className="text-right font-mono text-xs">
                                                {trade.quantity.toFixed(8)}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <span className={cn(
                                                    "font-mono text-xs font-medium",
                                                    isWin ? "text-green-500" : "text-red-500"
                                                )}>
                                                    {isWin ? "+" : ""}{trade.pnl.toFixed(3)} ({trade.pnl_percent.toFixed(2)}%)
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-muted-foreground hover:text-primary"
                                                    onClick={() => setSelectedTrade(trade)}
                                                >
                                                    <Eye className="h-4 w-4" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })
                            )}
                        </TableBody>
                    </Table>
                </div>
                {/* Pagination Controls could be added here */}
                <div className="flex justify-end p-2 gap-2">
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Previous</Button>
                    <span className="text-sm py-2 px-2 text-muted-foreground">Page {page} of {totalPages || 1}</span>
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages || totalPages === 0}>Next</Button>
                </div>
            </CardContent>

            <Dialog open={!!selectedTrade} onOpenChange={(open) => !open && setSelectedTrade(null)}>
                <DialogContent className="max-w-[600px] max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Trade Entry Details</DialogTitle>
                        <DialogDescription>
                            Technical conditions triggering this {selectedTrade?.side} position on {selectedTrade?.symbol}
                        </DialogDescription>
                    </DialogHeader>
                    {selectedTrade && (
                        <div className="space-y-4 py-4">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div className="space-y-1">
                                    <Label className="text-muted-foreground">Entry Time</Label>
                                    <p className="font-mono">{new Date(selectedTrade.entry_time).toLocaleString()}</p>
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-muted-foreground">Entry Price</Label>
                                    <p className="font-mono">${selectedTrade.entry_price}</p>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label>Entry Reason & Indicators</Label>
                                {selectedTrade.entry_reason ? (
                                    <div className="bg-muted/50 p-4 rounded-md overflow-x-auto border border-border">
                                        <pre className="text-xs font-mono">
                                            {JSON.stringify(selectedTrade.entry_reason, null, 2)}
                                        </pre>
                                    </div>
                                ) : (
                                    <div className="bg-muted/20 p-4 rounded-md text-center text-muted-foreground text-xs border border-dashed">
                                        No entry metadata.
                                    </div>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label>Exit Reason & Indicators</Label>
                                {selectedTrade.exit_reason ? (
                                    <div className="bg-muted/50 p-4 rounded-md overflow-x-auto border border-border">
                                        <pre className="text-xs font-mono">
                                            {JSON.stringify(selectedTrade.exit_reason, null, 2)}
                                        </pre>
                                    </div>
                                ) : (
                                    <div className="bg-muted/20 p-4 rounded-md text-center text-muted-foreground text-xs border border-dashed">
                                        No exit metadata.
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </Card>
    );
});

PositionLogTable.displayName = 'PositionLogTable';
