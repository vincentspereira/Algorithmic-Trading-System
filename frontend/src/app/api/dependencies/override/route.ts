
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const { dependency, action } = await request.json();

  // TODO: Implement manual override logic here
  console.log(`Manual override for ${dependency}: ${action}`);

  return NextResponse.json({ message: 'Override request received' });
}
