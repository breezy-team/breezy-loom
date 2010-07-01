Loom, a plugin for bzr to assist in developing focused patches.
Copyright (C) 2006, 2007, 2008 Canonical Limited.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as published
by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA


The bzr loom plugin
+++++++++++++++++++

Introduction
============

Loom is a Bazaar plugin that helps you to manage and develop patches.

It is similar to tools such as Quilt, Stacked Git and Mercurial Queues. However,
it also gives you the full power of version control when managing your stack of 
patches. This makes collaboration just as easy as if you were working with a
normal Bazaar branch. Using Loom, you can roll back, annotate, push and pull the
stack you're building.

The name "Loom" is appropriate because the tool works in two dimensions:

 * Up and down: similar to Quilt, Stacked Git and Mercurial Queues, allowing you
   to manage a stack of patches.
 * Time: Loom records the changes to your stack of patches over time, just like
   the version history of a standard Bazaar branch. This lets you push, pull and
   merge your stack with other developers.
   
That version history of each patch is a thread running through your loom.


Commands
========

 * loomify: prepares a standard Bazaar branch for use as a loom. It converts the
   branch's format so you must have the Loom plugin to work on the branch.
   
 * create-thread: adds a new thread, with the supplied name, to the loom and
   makes that the current thread.
   
 * record: similar to a standard bzr commit, this records the current stack of
   patches into the loom's version history, allowing it to be pushed, pulled
   and merged.
   
 * revert-loom: revert all changes in the current stack of patches to the last
   recorded version.
   
 * show-loom: list the threads in the loom. In future, this will also show the
   number of commits in each thread.
   
 * down-thread: start working on the next thread down so that commits and merges
   affect the newly selected thread.
 
 * up-thread: start working on the next thread up. Any changes in the current
   thread will be merged, ready to commit.
   
 * combine-thread: combine the current thread with the thread below it. If the
   current thread is the last one, this will produce an error message. In future,
   it will turn the loom into a normal branch.

The existing Bazaar command 'push' and 'branch' will create a new loom branch from
an existing loom. 

Pushing a loom into a standard branch will not convert it. Instead, it will push
the current thread into the standard branch. Similarly, pulling from a standard
branch will pull into the current thread of a loom. This assymetry makes it easy
to work with developers who are not using looms.

Loom also adds new revision specifiers 'thread:' and 'below:'. You can use these
to diff against threads in the current Loom. For instance, 'bzr diff -r
thread:' will show you the different between the thread below yours, and your
thread. See ``bzr help revisionspec`` for the detailed help on these two
revision specifiers.


Documentation
=============

The HOWTO provides a small but growing manual for Loom.


Internals
=========

XXX: In development

Why we dont use the revision_id to index into the loom:
# XXX: possibly we should use revision_id to determine what the
# loom looked like when it was committed, rather than taking a
# revision id in the loom branch. This suggests recording the 
# loom revision when writing a commit to a warp, which would mean
# that commit() could not do record() - we would have to record 
# a loom revision that was not yet created.
