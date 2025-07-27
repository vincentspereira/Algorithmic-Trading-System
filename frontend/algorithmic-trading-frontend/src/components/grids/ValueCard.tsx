"use client";

import { Card, CardContent, Typography, CircularProgress } from '@mui/material';

interface ValueCardProps {
    title: string;
    value?: number;
    isLoading: boolean;
    isError: boolean;
}

export const ValueCard = ({ title, value, isLoading, isError }: ValueCardProps) => {
    return (
        <Card>
            <CardContent>
                <Typography variant="h6" color="text.secondary">
                    {title}
                </Typography>
                {isLoading && <CircularProgress />}
                {isError && <Typography color="error">Error loading data</Typography>}
                {!isLoading && !isError && (
                    <Typography variant="h4">
                        {value?.toLocaleString('en-US', {
                            style: 'currency',
                            currency: 'USD',
                        })}
                    </Typography>
                )}
            </CardContent>
        </Card>
    );
};