import { render, screen } from "@testing-library/react";
import PostCard from "./PostCard";
import type { Post } from "@/types/movie";

const mockPost: Post = {
  id: 1,
  name: "The Matrix",
  author: "Wachowski Sisters",
  category: "Sci-Fi",
  rating: 9,
  lastUpdateTime: "2024-01-15",
};

describe("PostCard", () => {
  it("renders post heading and metadata", () => {
    render(<PostCard post={mockPost} />);
    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
      "The Matrix"
    );
    expect(screen.getByText("Wachowski Sisters")).toBeInTheDocument();
  });

  it("renders category, rating, and date as meta items", () => {
    render(<PostCard post={mockPost} />);
    expect(screen.getByText("Sci-Fi")).toBeInTheDocument();
    expect(screen.getByText("Rating: 9")).toBeInTheDocument();
  });

  it("renders without crashing when fields are empty or zero", () => {
    const edgeCasePost: Post = {
      ...mockPost,
      name: "",
      rating: 0,
    };
    render(<PostCard post={edgeCasePost} />);
    expect(screen.getByText("Rating: 0")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3 })).toBeInTheDocument();
  });
});
