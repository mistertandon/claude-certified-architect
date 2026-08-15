import { NextResponse } from "next/server";
import { fetchPosts } from "@/lib/tmdb";

export async function GET() {
  try {
    const data = await fetchPosts();
    return NextResponse.json(data, {
      headers: {
        "Cache-Control": "public, s-maxage=7200, stale-while-revalidate=3600",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch posts" },
      { status: 500 }
    );
  }
}
