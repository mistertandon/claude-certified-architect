import type { Post } from "@/types/movie";

const POSTS_API_URL = "http://localhost:4000/posts";

export async function fetchPosts(): Promise<Post[]> {
  const response = await fetch(POSTS_API_URL, {
    next: { revalidate: 7200 },
  });

  if (!response.ok) {
    throw new Error(`Posts API error: ${response.status}`);
  }

  return response.json();
}
