"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createOrgSchema, type CreateOrgFormValues } from "../schemas";
import { useCreateOrganization } from "../hooks";

export function CreateOrgDialog() {
  const [open, setOpen] = useState(false);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateOrgFormValues>({ resolver: zodResolver(createOrgSchema) });
  const createOrg = useCreateOrganization();

  const onSubmit = (values: CreateOrgFormValues) => {
    createOrg.mutate(
      { name: values.name, slug: values.slug || undefined },
      {
        onSuccess: () => {
          toast.success("Organization created.");
          reset();
          setOpen(false);
        },
        onError: (error) => toast.error(error.message || "Could not create organization."),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger className="inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium border">
            <Plus className="mr-2 h-4 w-4" />
            New Organization
        </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create organization</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" {...register("name")} />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="slug">Slug (optional)</Label>
            <Input id="slug" placeholder="auto-generated-if-empty" {...register("slug")} />
            {errors.slug && <p className="text-sm text-destructive">{errors.slug.message}</p>}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createOrg.isPending}>
              {createOrg.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}